from evennia import Command, default_cmds
from world.wod20th.models import Stat, SHIFTER_IDENTITY_STATS, SHIFTER_RENOWN, calculate_willpower, calculate_road
from evennia.utils import search
import re
from commands.CmdLanguage import CmdLanguage

class CmdSelfStat(default_cmds.MuxCommand):
    """
    Usage:
      +selfstat <stat>[(<instance>)]/<category>=[+-]<value>
      +selfstat <stat>[(<instance>)]/<category>=

    Examples:
      +selfstat Strength/Physical=+1
      +selfstat Firearms/Skill=-1
      +selfstat Status(Ventrue)/Social=
    """

    key = "+selfstat"
    aliases = ["selfstat"]
    locks = "cmd:all()"  # All players can use this command
    help_category = "Character"

    def parse(self):
        """
        Parse the arguments.
        """
        self.stat_name = ""
        self.instance = None
        self.category = None
        self.value_change = None
        self.temp = False

        try:
            args = self.args.strip()

            if '=' in args:
                first_part, second_part = args.split('=', 1)
                self.value_change = second_part.strip()
            else:
                first_part = args

            try:
                if '(' in first_part and ')' in first_part:
                    self.stat_name, instance_and_category = first_part.split('(', 1)
                    self.instance, self.category = instance_and_category.split(')', 1)
                    self.category = self.category.lstrip('/').strip() if '/' in self.category else None
                else:
                    parts = first_part.split('/')
                    if len(parts) == 2:
                        self.stat_name, self.category = parts
                    else:
                        self.stat_name = parts[0]

                self.stat_name = self.stat_name.strip()
                self.instance = self.instance.strip() if self.instance else None
                self.category = self.category.strip() if self.category else None

            except ValueError:
                self.stat_name = first_part.strip()

        except ValueError:
            self.stat_name = self.value_change = self.instance = self.category = None

    def initialize_stats(self, splat):
        """Initialize the basic stats structure based on splat type."""
        # Base structure common to all splats
        base_stats = {
            'other': {'splat': {'Splat': {'perm': splat, 'temp': splat}}},
            'identity': {'personal': {}, 'lineage': {}},
            'abilities': {'ability': {}},
            'attributes': {'physical': {}, 'social': {}, 'mental': {}},
            'backgrounds': {'background': {}},
            'merits': {},
            'flaws': {},
            'powers': {}, 
            'pools': {'dual': {}, 'moral': {}},
            'virtues': {'moral': {}},
            'archetype': {'personal': {}}  # For Nature/Demeanor
        }

        # Splat-specific additions
        if splat.lower() == 'vampire':
            base_stats['powers']['discipline'] = {}
            base_stats['pools']['dual']['Blood'] = {'perm': 10, 'temp': 10}  # Default to 13th generation
            base_stats['pools']['dual']['Willpower'] = {'perm': 1, 'temp': 1}
            base_stats['pools']['moral']['Road'] = {'perm': 1, 'temp': 1}
            
        elif splat.lower() == 'mage':
            base_stats['powers']['sphere'] = {}
            base_stats['pools']['dual']['Arete'] = {'perm': 1, 'temp': 1}
            base_stats['pools']['dual']['Quintessence'] = {'perm': 1, 'temp': 1}
            base_stats['pools']['dual']['Willpower'] = {'perm': 1, 'temp': 1}
            
        elif splat.lower() == 'shifter':
            base_stats['powers']['gift'] = {}
            base_stats['powers']['rite'] = {}
            base_stats['pools']['dual']['Rage'] = {'perm': 1, 'temp': 1}
            base_stats['pools']['dual']['Gnosis'] = {'perm': 1, 'temp': 1}
            base_stats['pools']['dual']['Willpower'] = {'perm': 1, 'temp': 1}
            base_stats['advantages'] = {'renown': {}}
            
        elif splat.lower() == 'changeling':
            base_stats['powers']['art'] = {}
            base_stats['powers']['realm'] = {}
            base_stats['pools']['dual']['Glamour'] = {'perm': 1, 'temp': 1}
            base_stats['pools']['dual']['Banality'] = {'perm': 1, 'temp': 1}
            base_stats['pools']['dual']['Willpower'] = {'perm': 1, 'temp': 1}
        
        else:  # Mortal or other
            base_stats['pools']['dual']['Willpower'] = {'perm': 1, 'temp': 1}

        # Initialize basic attributes with default value of 1
        for category in ['physical', 'social', 'mental']:
            if category == 'physical':
                attrs = ['Strength', 'Dexterity', 'Stamina']
            elif category == 'social':
                attrs = ['Charisma', 'Manipulation', 'Appearance']
            else:  # mental
                attrs = ['Perception', 'Intelligence', 'Wits']
            
            for attr in attrs:
                base_stats['attributes'][category][attr] = {'perm': 1, 'temp': 1}

        return base_stats

    def func(self):
        """Execute the command."""
        # Check if character is approved
        if self.caller.db.approved:
            self.caller.msg("|rError: Approved characters cannot use chargen commands. Please contact staff for any needed changes.|n")
            return

        if not self.stat_name:
            self.caller.msg("|rUsage: +selfstat <stat>[(<instance>)]/[<category>]=[+-]<value>|n")
            return

        # Get the stat definition
        stat = Stat.objects.filter(name__iexact=self.stat_name).first()
        if not stat:
            # If exact match fails, try a case-insensitive contains search
            matching_stats = Stat.objects.filter(name__icontains=self.stat_name)
            if matching_stats.count() > 1:
                stat_names = [s.name for s in matching_stats]
                self.caller.msg(f"Multiple stats match '{self.stat_name}': {', '.join(stat_names)}. Please be more specific.")
                return
            stat = matching_stats.first()
            if not stat:
                self.caller.msg(f"Stat '{self.stat_name}' not found.")
                return

        # Special handling for Shifter Rank
        if stat.name == 'Rank':
            splat = self.caller.db.stats.get('other', {}).get('splat', {}).get('Splat', {}).get('perm', '')
            if splat and splat == 'Shifter':
                stat.category = 'identity'
                stat.stat_type = 'lineage'

        # Check if the character can have this ability
        if stat.stat_type == 'ability' and not self.caller.can_have_ability(stat.name):
            self.caller.msg(f"Your character cannot have the {stat.name} ability.")
            return

        # Use the canonical name from the database
        self.stat_name = stat.name
        
        # Handle instances for background stats
        if stat.instanced:
            if not self.instance:
                self.caller.msg(f"The stat '{self.stat_name}' requires an instance. Use the format: {self.stat_name}(instance)")
                return
            full_stat_name = f"{self.stat_name}({self.instance})"
        else:
            if self.instance:
                self.caller.msg(f"The stat '{self.stat_name}' does not support instances.")
                return
            full_stat_name = self.stat_name

        # Handle stat removal (empty value)
        if self.value_change == '':
            if stat.category in self.caller.db.stats and stat.stat_type in self.caller.db.stats[stat.category]:
                if full_stat_name in self.caller.db.stats[stat.category][stat.stat_type]:
                    # For language-related stats, pass 0 instead of removing directly
                    if (full_stat_name == 'Language' or 
                        full_stat_name.startswith('Language(') or 
                        full_stat_name == 'Natural Linguist'):
                        self.caller.set_stat(stat.category, stat.stat_type, full_stat_name, 0)
                    else:
                        del self.caller.db.stats[stat.category][stat.stat_type][full_stat_name]
                    self.caller.msg(f"|gRemoved stat '{full_stat_name}'.|n")
                    return
                else:
                    self.caller.msg(f"|rStat '{full_stat_name}' not found.|n")
                    return

        # Special handling for Appearance stat
        if stat.name == 'Appearance':
            splat = self.caller.db.stats.get('other', {}).get('splat', {}).get('Splat', {}).get('perm', '')
            clan = self.caller.db.stats.get('identity', {}).get('lineage', {}).get('Clan', {}).get('perm', '')
            
            if splat and splat == 'Vampire' and clan in ['Nosferatu', 'Samedi']:
                self.caller.msg("Nosferatu and Samedi vampires always have Appearance 0.")
                return
            
            if splat and splat == 'Shifter':
                form = self.caller.db.stats.get('other', {}).get('form', {}).get('Form', {}).get('temp', '')
                if form == 'Crinos':
                    self.caller.msg("Characters in Crinos form always have Appearance 0.")
                    return

        # Handle incremental changes
        try:
            if self.value_change.startswith('+') or self.value_change.startswith('-'):
                current_value = self.caller.get_stat(stat.category, stat.stat_type, full_stat_name)
                if current_value is None:
                    current_value = 0
                new_value = current_value + int(self.value_change)
            else:
                new_value = int(self.value_change) if self.value_change.isdigit() else self.value_change
        except (ValueError, TypeError):
            new_value = self.value_change

        # Update the stat
        try:
            self.caller.set_stat(stat.category, stat.stat_type, full_stat_name, new_value, temp=False)
            
            # During character generation (when character is not approved), 
            # always set temp value equal to permanent value
            if not self.caller.db.approved:
                self.caller.set_stat(stat.category, stat.stat_type, full_stat_name, new_value, temp=True)
                self.caller.msg(f"|gUpdated {full_stat_name} to {new_value} (both permanent and temporary).|n")
                
                # Check if this is a language-related merit change
                if (full_stat_name == 'Language' or 
                    full_stat_name.startswith('Language(') or 
                    full_stat_name == 'Natural Linguist'):
                    # Validate languages after merit change
                    cmd_lang = CmdLanguage()
                    cmd_lang.caller = self.caller
                    if cmd_lang.validate_languages():
                        cmd_lang.list_languages()
            
            # If already approved, only update temp for pools and dual stats
            elif stat.category == 'pools' or stat.stat_type == 'dual':
                self.caller.set_stat(stat.category, stat.stat_type, full_stat_name, new_value, temp=True)
                self.caller.msg(f"|gUpdated {full_stat_name} to {new_value} (both permanent and temporary).|n")
            else:
                self.caller.msg(f"|gUpdated {full_stat_name} to {new_value}.|n")

            # After setting a stat, recalculate Willpower and Road
            if full_stat_name in ['Courage', 'Self-Control', 'Conscience', 'Conviction', 'Instinct']:
                new_willpower = calculate_willpower(self.caller)
                # Set both permanent and temporary values for Willpower
                self.caller.set_stat('pools', 'dual', 'Willpower', new_willpower, temp=False)
                self.caller.set_stat('pools', 'dual', 'Willpower', new_willpower, temp=True)
                self.caller.msg(f"|gRecalculated Willpower to {new_willpower}.|n")

                new_road = calculate_road(self.caller)
                self.caller.set_stat('pools', 'moral', 'Road', new_road, temp=False)
                self.caller.msg(f"|gRecalculated Road to {new_road}.|n")

        except ValueError as e:
            self.caller.msg(str(e))

        # When setting splat for the first time
        if self.stat_name.lower() == 'splat':
            if not self.value_change:
                self.caller.msg("You must specify a splat type.")
                return
            
            # Initialize the stats structure based on splat
            self.caller.db.stats = self.initialize_stats(self.value_change)
            self.caller.msg(f"|gInitialized character as {self.value_change} with basic stats.|n")
            return