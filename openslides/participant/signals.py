# -*- coding: utf-8 -*-

from django import forms
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.dispatch import receiver
from django.utils.translation import ugettext as _
from django.utils.translation import ugettext_lazy, ugettext_noop

from openslides.config.api import ConfigGroup, ConfigGroupedCollection, ConfigVariable
from openslides.config.signals import config_signal
from openslides.core.signals import post_database_setup

from .api import create_or_reset_admin_user
from .models import Group


@receiver(config_signal, dispatch_uid='setup_participant_config')
def setup_participant_config(sender, **kwargs):
    """
    Participant config variables.
    """
    # General
    participant_sort_users_by_first_name = ConfigVariable(
        name='participant_sort_users_by_first_name',
        default_value=False,
        form_field=forms.BooleanField(
            required=False,
            label=ugettext_lazy('Sort participants by first name'),
            help_text=ugettext_lazy('Disable for sorting by last name')))

    group_general = ConfigGroup(
        title=ugettext_lazy('Sorting'),
        variables=(participant_sort_users_by_first_name,))

    # PDF
    participant_pdf_welcometitle = ConfigVariable(
        name='participant_pdf_welcometitle',
        default_value=_('Welcome to OpenSlides!'),
        translatable=True,
        form_field=forms.CharField(
            widget=forms.Textarea(),
            required=False,
            label=ugettext_lazy('Title for access data and welcome PDF')))

    participant_pdf_welcometext = ConfigVariable(
        name='participant_pdf_welcometext',
        default_value=_('[Place for your welcome and help text.]'),
        translatable=True,
        form_field=forms.CharField(
            widget=forms.Textarea(),
            required=False,
            label=ugettext_lazy('Help text for access data and welcome PDF')))

    participant_pdf_url = ConfigVariable(
        name='participant_pdf_url',
        default_value='http://example.com:8000',
        form_field=forms.CharField(
            widget=forms.TextInput(),
            required=False,
            label=ugettext_lazy('System URL'),
            help_text=ugettext_lazy('Used for QRCode in PDF of access data.')))

    participant_pdf_wlan_ssid = ConfigVariable(
        name='participant_pdf_wlan_ssid',
        default_value='',
        form_field=forms.CharField(
            widget=forms.TextInput(),
            required=False,
            label=ugettext_lazy('WLAN name (SSID)'),
            help_text=ugettext_lazy('Used for WLAN QRCode in PDF of access data.')))

    participant_pdf_wlan_password = ConfigVariable(
        name='participant_pdf_wlan_password',
        default_value='',
        form_field=forms.CharField(
            widget=forms.TextInput(),
            required=False,
            label=ugettext_lazy('WLAN password'),
            help_text=ugettext_lazy('Used for WLAN QRCode in PDF of access data.')))

    participant_pdf_wlan_encryption = ConfigVariable(
        name='participant_pdf_wlan_encryption',
        default_value='',
        form_field=forms.ChoiceField(
            widget=forms.Select(),
            required=False,
            label=ugettext_lazy('WLAN encryption'),
            help_text=ugettext_lazy('Used for WLAN QRCode in PDF of access data.'),
            choices=(
                ('', '---------'),
                ('WEP', 'WEP'),
                ('WPA', 'WPA/WPA2'),
                ('nopass', ugettext_lazy('No encryption')))))

    group_pdf = ConfigGroup(
        title=ugettext_lazy('PDF'),
        variables=(participant_pdf_welcometitle,
                   participant_pdf_welcometext,
                   participant_pdf_url,
                   participant_pdf_wlan_ssid,
                   participant_pdf_wlan_password,
                   participant_pdf_wlan_encryption))

    return ConfigGroupedCollection(
        title=ugettext_noop('Participant'),
        url='participant',
        required_permission='config.can_manage',
        weight=50,
        groups=(group_general, group_pdf))


@receiver(post_database_setup, dispatch_uid='participant_create_builtin_groups_and_admin')
def create_builtin_groups_and_admin(sender, **kwargs):
    """
    Creates the buildin groups and the admin user.

    Creates the builtin groups: Anonymous, Registered, Delegates and Staff.

    Creates the builtin user: admin.
    """
    # Check whether the group pks 1 to 4 are free
    if Group.objects.filter(pk__in=range(1, 5)).exists():
        # Do completely nothing if there are already some of our groups in the database.
        return

    # Anonymous and Registered
    ct_core = ContentType.objects.get(app_label='core', model='customslide')
    perm_1 = Permission.objects.get(content_type=ct_core, codename='can_see_projector')
    perm_2 = Permission.objects.get(content_type=ct_core, codename='can_see_dashboard')

    ct_agenda = ContentType.objects.get(app_label='agenda', model='item')
    ct_speaker = ContentType.objects.get(app_label='agenda', model='speaker')
    perm_3 = Permission.objects.get(content_type=ct_agenda, codename='can_see_agenda')
    perm_3a = Permission.objects.get(content_type=ct_agenda, codename='can_see_orga_items')
    can_speak = Permission.objects.get(content_type=ct_speaker, codename='can_be_speaker')

    ct_motion = ContentType.objects.get(app_label='motion', model='motion')
    perm_4 = Permission.objects.get(content_type=ct_motion, codename='can_see_motion')

    ct_assignment = ContentType.objects.get(app_label='assignment', model='assignment')
    perm_5 = Permission.objects.get(content_type=ct_assignment, codename='can_see_assignment')

    ct_participant = ContentType.objects.get(app_label='participant', model='user')
    perm_6 = Permission.objects.get(content_type=ct_participant, codename='can_see_participant')

    ct_mediafile = ContentType.objects.get(app_label='mediafile', model='mediafile')
    perm_6a = Permission.objects.get(content_type=ct_mediafile, codename='can_see')

    group_anonymous = Group.objects.create(name=ugettext_noop('Anonymous'), pk=1)
    group_anonymous.permissions.add(perm_1, perm_2, perm_3, perm_3a, perm_4, perm_5, perm_6, perm_6a)
    group_registered = Group.objects.create(name=ugettext_noop('Registered'), pk=2)
    group_registered.permissions.add(perm_1, perm_2, perm_3, perm_3a, perm_4, perm_5, perm_6, perm_6a, can_speak)

    # Delegates
    perm_7 = Permission.objects.get(content_type=ct_motion, codename='can_create_motion')
    perm_8 = Permission.objects.get(content_type=ct_motion, codename='can_support_motion')
    perm_9 = Permission.objects.get(content_type=ct_assignment, codename='can_nominate_other')
    perm_10 = Permission.objects.get(content_type=ct_assignment, codename='can_nominate_self')
    perm_10a = Permission.objects.get(content_type=ct_mediafile, codename='can_upload')

    group_delegates = Group.objects.create(name=ugettext_noop('Delegates'), pk=3)
    group_delegates.permissions.add(perm_7, perm_8, perm_9, perm_10, perm_10a)

    # Staff
    perm_11 = Permission.objects.get(content_type=ct_agenda, codename='can_manage_agenda')
    perm_12 = Permission.objects.get(content_type=ct_motion, codename='can_manage_motion')
    perm_13 = Permission.objects.get(content_type=ct_assignment, codename='can_manage_assignment')
    perm_14 = Permission.objects.get(content_type=ct_participant, codename='can_manage_participant')
    perm_15 = Permission.objects.get(content_type=ct_core, codename='can_manage_projector')
    perm_15a = Permission.objects.get(content_type=ct_mediafile, codename='can_manage')

    ct_config = ContentType.objects.get(app_label='config', model='configstore')
    perm_16 = Permission.objects.get(content_type=ct_config, codename='can_manage')

    group_staff = Group.objects.create(name=ugettext_noop('Staff'), pk=4)
    group_staff.permissions.add(perm_7, perm_9, perm_10, perm_10a, perm_11, perm_12, perm_13, perm_14, perm_15, perm_15a, perm_16)
    group_staff.permissions.add(perm_6)  # TODO: Remove this redundancy after cleanup of the permission system

    # Admin user
    create_or_reset_admin_user()
