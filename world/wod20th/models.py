# mygame/server/conf/models.py
import re
from django.db import models
from django.db.models import JSONField  # Use the built-in JSONField
from django.forms import ValidationError
from evennia.locks.lockhandler import LockHandler
from django.conf import settings
from evennia.accounts.models import AccountDB
from evennia.objects.models import ObjectDB
from evennia.utils.idmapper.models import SharedMemoryModel
from typing import Dict, List, Union

# Define predefined categories and extended stat types
CATEGORIES = [
    ('attributes', 'Attributes'),
    ('abilities', 'Abilities'),
    ('secondary_abilities', 'Secondary Abilities'),
    ('advantages', 'Advantages'),
    ('backgrounds', 'Backgrounds'),
    ('powers', 'Powers'),
    ('merits', 'Merits'),
    ('flaws', 'Flaws'),
    ('traits', 'Traits'),
    ('identity', 'Identity'),
    ('archetype', 'Archetype'),
    ('virtues', 'Virtues'),
    ('legacy', 'Legacy'),
    ('pools', 'Pools'),
    ('other', 'Other')
]

STAT_TYPES = [
    ('attribute', 'Attribute'),
    ('ability', 'Ability'),
    ('secondary_ability', 'Secondary Ability'),
    ('advantage', 'Advantage'),
    ('background', 'Background'),
    ('lineage', 'Lineage'),
    ('discipline', 'Discipline'),
    ('combodiscipline', 'Combo Discipline'),
    ('gift', 'Gift'),
    ('rite', 'Rite'),
    ('sphere', 'Sphere'),
    ('rote', 'Rote'),
    ('art', 'Art'),
    ('splat', 'Splat'),
    ('edge', 'Edge'),
    ('discipline', 'Discipline'),
    ('realm', 'Realm'),
    ('sphere', 'Sphere'),
    ('art', 'Art'),
    ('path', 'Path'),
    ('enlightenment', 'Enlightenment'),
    ('power', 'Power'),
    ('other', 'Other'),
    ('virtue', 'Virtue'),
    ('vice', 'Vice'),
    ('merit', 'Merit'),
    ('flaw', 'Flaw'),
    ('trait', 'Trait'),
    ('skill', 'Skill'),
    ('knowledge', 'Knowledge'),
    ('talent', 'Talent'),
    ('secondary_knowledge', 'Secondary Knowledge'),
    ('secondary_talent', 'Secondary Talent'),
    ('secondary_skill', 'Secondary Skill'),
    ('specialty', 'Specialty'),
    ('other', 'Other'),
    ('physical', 'Physical'),
    ('social', 'Social'),
    ('mental', 'Mental'),
    ('personal', 'Personal'),
    ('supernatural', 'Supernatural'),
    ('moral', 'Moral'),
    ('temporary', 'Temporary'),
    ('dual', 'Dual'),
    ('renown', 'Renown'),
    ('arete', 'Arete'),
    ('banality', 'Banality'),
    ('glamour', 'Glamour'),
    ('essence', 'Essence'),
    ('quintessence', 'Quintessence'),
    ('paradox', 'Paradox'),
    ('kith', 'Kith'),
    ('seeming', 'Seeming'),
    ('house', 'House'),
    ('seelie-legacy', 'Seelie Legacy'),
    ('unseelie-legacy', 'Unseelie Legacy')
]

class Stat(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(default='')  # Changed to non-nullable with default empty string
    game_line = models.CharField(max_length=100)
    category = models.CharField(max_length=100, choices=CATEGORIES)
    stat_type = models.CharField(max_length=100, choices=STAT_TYPES)
    values = JSONField(default=list, blank=True, null=True)
    lock_string = models.CharField(max_length=255, blank=True, null=True)
    splat = models.CharField(max_length=100, blank=True, null=True, default=None)
    hidden = models.BooleanField(default=False)
    locked = models.BooleanField(default=False)
    instanced = models.BooleanField(default=False, null=True)
    # add a field for the default value of the stat
    default = models.CharField(max_length=100, blank=True, null=True, default=None)

    def __str__(self):
        return self.name

    @property
    def lock_storage(self):
        """
        Mimics the lock_storage attribute expected by LockHandler.
        """
        return self.lock_string or ""

    def can_access(self, accessing_obj, access_type):
        """
        Check if the accessing_obj can access this Stat based on the lock_string.
        """
        # Create a temporary lock handler to handle the lock check
        temp_lock_handler = LockHandler(self)
        
        # Perform the access check
        return temp_lock_handler.check(accessing_obj, access_type)

    def save(self, *args, **kwargs):
        if self.stat_type == 'renown':
            # Ensure renown stats use the dual value structure
            if self.name in SHIFTER_RENOWN:
                self.values = SHIFTER_RENOWN[self.name]
        super().save(*args, **kwargs)

    class Meta:
        app_label = 'wod20th'

class CharacterSheet(SharedMemoryModel):
    account = models.OneToOneField(AccountDB, related_name='character_sheet', on_delete=models.CASCADE, null=True)
    character = models.OneToOneField(ObjectDB, related_name='character_sheet', on_delete=models.CASCADE, null=True, unique=True)
    db_object = models.OneToOneField('objects.ObjectDB', related_name='db_character_sheet', on_delete=models.CASCADE, null=True)

    class Meta:
        app_label = 'wod20th'


from django.db import models
from evennia.utils.idmapper.models import SharedMemoryModel

"""
class Note(models.Model):
    owner = models.ForeignKey('objects.ObjectDB', related_name='notes', on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    text = models.TextField()
    category = models.CharField(max_length=50, default='General')
    is_public = models.BooleanField(default=False)
    is_approved = models.BooleanField(default=False)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    character_note_id = models.IntegerField(default=1)

    class Meta:
        app_label = 'wod20th'
        unique_together = ('owner', 'character_note_id')

    def save(self, *args, **kwargs):
        if not self.pk:  # Only for new notes
            # Get the highest character_note_id for this owner
            highest = Note.objects.filter(owner=self.owner).aggregate(
                models.Max('character_note_id'))['character_note_id__max']
            self.character_note_id = (highest or 0) + 1
        super().save(*args, **kwargs)

    @property
    def id(self):
        #Override to return character-specific ID

        return self.character_note_id
        """

def calculate_willpower(character):
    """Calculate Willpower based on virtues."""
    try:
        # Get the character's virtues
        virtues = character.db.stats.get('virtues', {}).get('moral', {})
        
        # Get Courage value (common to all paths)
        courage = virtues.get('Courage', {}).get('perm', 0)
        
        # Get the other relevant virtue based on path
        enlightenment = character.get_stat('identity', 'personal', 'Enlightenment')
        
        if enlightenment and enlightenment != 'Humanity':
            # For most non-Humanity paths
            conviction = virtues.get('Conviction', {}).get('perm', 0)
            willpower = courage + conviction
        else:
            # For Humanity and paths using Conscience
            conscience = virtues.get('Conscience', {}).get('perm', 0)
            willpower = courage + conscience
            
        return willpower if willpower > 0 else 1
        
    except (AttributeError, KeyError):
        return 1

def calculate_road(character):
    enlightenment = character.get_stat('identity', 'personal', 'Enlightenment', temp=False)
    virtues = character.db.stats.get('virtues', {}).get('moral', {})

    path_virtues = {
        'Humanity': ('Conscience', 'Self-Control'),
        'Night': ('Conviction', 'Instinct'),
        'Beast': ('Conviction', 'Instinct'),
        'Harmony': ('Conscience', 'Instinct'),
        'Evil Revelations': ('Conviction', 'Self-Control'),
        'Self-Focus': ('Conviction', 'Instinct'),
        'Scorched Heart': ('Conviction', 'Self-Control'),
        'Entelechy': ('Conviction', 'Self-Control'),
        'Sharia El-Sama': ('Conscience', 'Self-Control'),
        'Asakku': ('Conviction', 'Instinct'),
        'Death and the Soul': ('Conviction', 'Self-Control'),
        'Honorable Accord': ('Conscience', 'Self-Control'),
        'Feral Heart': ('Conviction', 'Instinct'),
        'Orion': ('Conviction', 'Instinct'),
        'Power and the Inner Voice': ('Conviction', 'Instinct'),
        'Lilith': ('Conviction', 'Instinct'),
        'Caine': ('Conviction', 'Instinct'),
        'Cathari': ('Conviction', 'Instinct'),
        'Redemption': ('Conscience', 'Self-Control'),
        'Metamorphosis': ('Conviction', 'Instinct'),
        'Bones': ('Conviction', 'Self-Control'),
        'Typhon': ('Conviction', 'Self-Control'),
        'Paradox': ('Conviction', 'Self-Control'),
        'Blood': ('Conviction', 'Self-Control'),
        'Hive': ('Conviction', 'Instinct')
    }

    if enlightenment in path_virtues:
        virtue1, virtue2 = path_virtues[enlightenment]
        value1 = virtues.get(virtue1, {}).get('perm', 0)
        value2 = virtues.get(virtue2, {}).get('perm', 0)
        return value1 + value2
    else:
        # If the enlightenment is not recognized, return 0 or a default value
        return 0

class ShapeshifterForm(models.Model):
    name = models.CharField(max_length=50)
    shifter_type = models.CharField(max_length=50)
    description = models.TextField()
    stat_modifiers = models.JSONField(default=dict)
    rage_cost = models.IntegerField(default=0)
    difficulty = models.IntegerField(default=6)
    lock_string = models.CharField(max_length=255, default='examine:all();control:perm(Admin)')

    class Meta:
        app_label = 'wod20th'
        unique_together = ('name', 'shifter_type')

    def __str__(self):
        return f"{self.shifter_type.capitalize()} - {self.name}"

    def clean(self):
        # Validate stat_modifiers
        if not isinstance(self.stat_modifiers, dict):
            raise ValidationError({'stat_modifiers': 'Must be a dictionary'})
        for key, value in self.stat_modifiers.items():
            if not isinstance(key, str) or not isinstance(value, int):
                raise ValidationError({'stat_modifiers': 'Keys must be strings and values must be integers'})

        # Validate difficulty
        if self.difficulty < 1 or self.difficulty > 10:
            raise ValidationError({'difficulty': 'Difficulty must be between 1 and 10'})

        # Allow underscores in form names
        if not re.match(r'^[\w\s_-]+$', self.name):
            raise ValidationError({'name': 'Form name can only contain letters, numbers, spaces, underscores, and hyphens'})

    def save(self, *args, **kwargs):
        self.clean()
        self.shifter_type = self.sanitize_shifter_type(self.shifter_type)
        super().save(*args, **kwargs)

    @staticmethod
    def sanitize_shifter_type(shifter_type):
        # Convert to lowercase and remove any non-alphanumeric characters except spaces and underscores
        sanitized = re.sub(r'[^\w\s_]', '', shifter_type.lower())
        # Replace spaces with underscores
        return re.sub(r'\s+', '_', sanitized)

class Asset(models.Model):
    ASSET_TYPES = [
        ('retainer', 'Retainer'),
        ('haven', 'Haven'),
        ('territory', 'Territory'),
        ('contact', 'Contact'),
    ]

    name = models.CharField(max_length=100, unique=True)
    asset_type = models.CharField(max_length=50, choices=ASSET_TYPES)
    description = models.TextField(blank=True, null=True)
    value = models.IntegerField(default=0)
    owner_id = models.IntegerField()  # Store the owner's ID instead of a ForeignKey
    status = models.CharField(max_length=50, default='Active')
    traits = models.JSONField(default=dict, blank=True, null=True)

    def __str__(self):  
        return f"{self.name} ({self.get_asset_type_display()})"

    class Meta:
        app_label = 'wod20th'

    @property
    def owner(self):
        from typeclasses.characters import Character  # Local import
        try:
            return Character.objects.get(id=self.owner_id)
        except Character.DoesNotExist:
            return None


class ActionTemplate(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField()
    downtime_cost = models.IntegerField(default=0)  # Cost in downtime hours
    requires_target = models.BooleanField(default=False)
    category = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        app_label = 'wod20th'   

class Action(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    template = models.ForeignKey(ActionTemplate, on_delete=models.CASCADE)
    character_id = models.IntegerField()  # Store the character's ID instead of a ForeignKey
    target_asset = models.ForeignKey(Asset, null=True, blank=True, on_delete=models.SET_NULL, related_name='targeted_by_actions')
    downtime_spent = models.IntegerField(default=0)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    result = models.TextField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.character_id} - {self.template.name} targeting {self.target_asset} ({self.get_status_display()})"

    class Meta:
        app_label = 'wod20th'

    @property
    def character(self):
        from typeclasses.characters import Character  # Local import
        try:
            return Character.objects.get(id=self.character_id)
        except Character.DoesNotExist:
            return None

    def perform_action(self):
        if self.status == 'pending':
            # Implement the logic to resolve the action
            self.status = 'completed'
            self.result = "Action completed successfully."
            self.save()

SHIFTER_IDENTITY_STATS = {
    "Garou": ["Tribe", "Breed", "Auspice", "Rank"],
    "Gurahl": ["Tribe", "Breed", "Auspice", "Rank"],
    "Rokea": ["Tribe", "Breed", "Auspice", "Rank"],
    "Ananasi": ["Aspect", "Ananasi Faction", "Breed", "Ananasi Cabal", "Rank"],
    "Ajaba": ["Aspect", "Breed", "Rank"],
    "Bastet": ["Tribe", "Breed", "Rank"],
    "Corax": ["Breed", "Rank"],
    "Kitsune": ["Kitsune Path", "Kitsune Faction", "Breed", "Rank"],
    "Mokole": ["Varnas", "Stream", "Breed", "Rank"],
    "Nagah": ["Crown", "Breed", "Auspice", "Rank"],
    "Nuwisha": ["Breed", "Rank"],
    "Ratkin": ["Aspect", "Plague", "Breed", "Rank"]
}
SHIFTER_RENOWN: Dict[str, Union[List[str], Dict[str, Dict[str, List[int]]]]] = {
    "Ajaba": ["Cunning", "Ferocity", "Obligation"],
    "Ananasi": ["Cunning", "Obedience", "Wisdom"],
    "Bastet": ["Cunning", "Ferocity", "Honor"],
    "Corax": ["Glory", "Honor", "Wisdom"],
    "Garou": ["Glory", "Honor", "Wisdom"],
    "Gurahl": ["Honor", "Succor", "Wisdom"],
    "Kitsune": ["Cunning", "Honor", "Glory"],
    "Mokole": ["Glory", "Honor", "Wisdom"],
    "Nagah": [],  # Nagah don't use Renown
    "Nuwisha": ["Humor", "Glory", "Cunning"],
    "Ratkin": ["Infamy", "Obligation", "Cunning"],
    "Rokea": ["Valor", "Harmony", "Innovation"]
}

CLAN = {
    'Brujah', 'Gangrel', 'Malkavian', 'Nosferatu', 'Toreador', 'Tremere', 'Ventrue', 'Lasombra', 
    'Tzimisce', 'Assamite', 'Followers of Set', 'Hecata', 'Ravnos', 'Baali', 'Blood Brothers', 
    'Daughters of Cacophony', 'Gargoyles', 'Kiasyd', 'Nagaraja', 'Salubri', 'Samedi', 'True Brujah'
}

MAGE_FACTION = {
    'Traditions', 'Technocracy', 'Nephandi'
}

MAGE_SPHERES = {
    'Correspondence', 'Entropy', 'Forces', 'Life', 'Matter', 'Mind', 'Prime', 'Spirit', 'Time'
}

TRADITION = {
    'Cultists of Ecstasy', 'Euthanatos', 'Celestial Chorus', 'Akashic Brotherhood',
    'Dreamspeakers', 'Virtual Adepts', 'Order of Hermes', 'Verbena',
    'Sons of Ether'
}

TRADITION_SUBFACTION = {
    'Akashic Brotherhood': [
        'Chabnagpa', 'Lin Shen', 'Wu Shan', 'Yamabushi', 'Jina', 'Karmachakra', 'Shaolin', 'Blue Skins',
        'Mo-Tzu Fa', "Roda d'Oro", 'Gam Lung', 'Han Fei Tzu Academy', 'Kaizankai', 'Banner of the Ebon Dragon', 
        'Sulsa', 'Tenshi Arashi Ryu', 'Wu Lung'
    ],
    'Celestial Chorus': [
        'Brothers of St. Christopher', 'Chevra Kedisha', 'Knights of St. George', 'Order of St. Michael', 
        'Poor Knights of the Temple of Solomon', 'Sisters of Gabrielle', 'Alexandrian Society', 'Anchorite',
        'Children of Albi', 'Latitudinarian', 'Monist', 'Nashimite', 'Septarian', 'Hare Krishna', 'Hindu',
        'Jain', 'Son of Mithras', 'Rastafarian', 'Sikh', 'Sufi', 'Bat Binah', 'Song of the Ancients'
    ],
    'Cultists of Ecstasy': [
        'Erzuli Jingo', 'Kiss of Astarte', 'Maenad', "K'an Lu", 'Vratyas', 'Aghoris', 'Acharne', 'Freyji',
        'Sons of Wotan', 'Sutr', 'Joybringers', 'Dissonance Society', 'Klubwerks', "Children's Crusade",
        'Cult of Acceptance', 'Silver Bridges', 'Los Sabios Locos', "Ka'a", 'Khlysty Flagellants', 
        "Bongo's Rangers", 'Dervish', 'Confrerie Chango', 'Roda do Jogo', 'Los Sangradores', 'Studiosi',
        'Umilyenye'
    ],
    'Euthanatos': [
        'Aided', 'Devasu', 'Lhakmist', 'Natatapa', 'Knight of Radamanthys', 'Pomegranate Deme', "N'anga",
        'Ta Kiti', 'Albireo', 'Chakramuni', 'Golden Chalice', 'Pallottino', 'Scholars of the Wheel', "Yggdrasil's Keepers",
        'Yum Cimil'
    ],
    'Dreamspeakers': [
        'Balomb', 'Baruti', 'Contrary', 'Four Winds', 'Ghost Wheel Society', 'Keeper of the Sacred Fire', 
        'Kopa Loei', 'Red Spear Society', 'Sheikha', 'Solitaries', 'Spirit Smith', 'Uzoma'
    ],
    'Order of Hermes': [
        'House Bonisagus', 'House Flambeau', 'House Fortunae', 'House Quaesitori', 'House Shaea', 'House Tytalus',
        'House Verditius', 'House Criamon', 'House Jerbiton', 'House Merinita', 'House Skopos', 'House Xaos'
    ],
    'Verbena': [
        'Gardeners of the Tree', 'Lifeweavers', 'Moon-Seekers', 'Twisters of Fate', 'Techno-Pagans', 'Fairy Folk', 'New Age'
    ],
    'Sons of Ether': [
        'Ethernauts', 'Cybernauts', 'Utopians', 'Adventurers', 'Mad Scientists', 'Progressivists', 'Aquanauts'
    ],
    'Virtual Adepts': [
        'Chaoticians', 'Cyberpunk', 'Cypherpunks', 'Nexplorers', 'Reality Coders'
    ]
}

CONVENTION = {
    'Iteration X', 'New World Order', 'Progenitor', 'Syndicate', 'Void Engineer'
}

METHODOLOGIES = {
    'Iteration X': [
        'BioMechanics', 'Macrotechnicians', 'Statisticians', 'Time-Motion Managers'
    ],
    'New World Order': [
        'Ivory Tower', 'Operatives', 'Watchers', 'The Feed', 'Q Division', 'Agronomists'
    ],
    'Progenitors': [
        'Applied Sciences', 'Deviancy Scene investigators', 'Médecins Sans Superstition',
        'Biosphere Explorers', 'Damage Control', 'Ethical Compliance', 'FACADE Engineers',
        'Genegineers', 'Pharmacopoeists', 'Preservationists', 'Psychopharmacopoeists', 
        'Shalihotran Society'
    ],
    'Syndicate': [
        'Disbursements', 'Assessment Division', 'Reorganization Division', 'Procurements Division',
        'Extraction Division', 'Enforcers (Hollow Men)', 'Legal Division', 'Extralegal Division',
        'Extranational Division', 'Information Specialists', 'Special Information Security Division',
        'Financiers', 'Acquisitions Division', 'Entrepreneurship Division', 'Liquidation Division',
        'Media Control', 'Effects Division', 'Spin Division', 'Marketing Division', 'Special Projects Division'
    ],
    'Void Engineer': [
        'Border Corps Division', 'Earth Frontier Division', 'Aquatic Exploration Teams',
        'Cryoregional Specialists', 'Hydrothermal Botanical Mosaic Analysts', 'Inaccessible High Elevation Exploration Teams',
        'Subterranean Exploration Corps', 'Neutralization Specialist Corps', 'Neutralization Specialists', 
        'Enforcement Training and Conditioning Agency', 'Department of Psychological Evaluation and Maintenance', 'Pan-Dimensional Corps', 
        'Deep Exploration Teams', 'Solar Exploration Teams', 'Cybernauts', 'Chrononauts', 'Research & Execution'
    ]
}

NEPHANDI_FACTION = {
    'Herald of the Basilisk', 'Obliviate', 'Malfean', 'Baphie', 
    'Infernalist', 'Ironhand', 'Mammonite', "K'llashaa"
}

SEEMING = {
    'Childing', 'Wilder', 'Grump'
}

KITH = {
    'Boggan', 'Clurichaun', 'Eshu', 'Nocker', 'Piskie', 'Pooka', 'Redcap', 'Satyr', 
    'Selkie', 'Arcadian Sidhe', 'Autumn Sidhe', 'Sluagh', 'Troll'
}

SEELIE_LEGACIES = {
    'Bumpkin', 'Courtier', 'Crafter', 'Dandy', 'Hermit', 'Orchid', 'Paladin', 'Panderer', 
    'Regent', 'Sage', 'Saint', 'Squire', 'Troubadour', 'Wayfarer'
}

UNSEELIE_LEGACIES = {
    'Beast', 'Fatalist', 'Fool', 'Grotesque', 'Knave', 'Outlaw', 'Pandora', 'Peacock', 'Rake', 'Riddler', 
    'Ringleader', 'Rogue', 'Savage', 'Wretch'
}

ARTS = {
    'Autumn', 'Chicanery', 'Chronos', 'Contract', 'Dragon’s Ire', 'Legerdemain', 'Metamorphosis', 'Naming', 
    'Oneiromancy', 'Primal', 'Pyretics', 'Skycraft', 'Soothsay', 'Sovereign', 'Spring', 'Summer', 'Wayfare', 'Winter'
}

REALMS = {
    'Actor', 'Fae', 'Nature', 'Prop', 'Scene', 'Time'
}

