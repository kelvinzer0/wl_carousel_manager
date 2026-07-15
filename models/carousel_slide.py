# -*- coding: utf-8 -*-
import logging
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class CarouselSlide(models.Model):
    _name = 'carousel.slide'
    _description = 'Carousel Slide'
    _order = 'sequence, id'
    _rec_name = 'title'

    title = fields.Char(string='Title', required=True, translate=True)
    subtitle = fields.Char(string='Subtitle', translate=True)
    cta_text = fields.Char(string='CTA Button Text', default='Pesan Sekarang',
                           translate=True)
    link_url = fields.Char(string='Link URL', default='/shop',
                           help='URL tujuan saat slide di-klik. Bisa internal '
                                '(/shop?category=6) atau external (https://...)')

    image_desktop = fields.Image(string='Desktop Image', required=True,
                                 max_width=1920, max_height=600,
                                 help='Ukuran ideal: 1920×600px (16:5 ratio)')
    image_mobile = fields.Image(string='Mobile Image',
                                max_width=750, max_height=800,
                                help='Ukuran ideal: 750×800px (portrait). '
                                     'Kosongkan untuk pakai desktop image.')

    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)
    start_date = fields.Datetime(string='Start Date',
                                 help='Auto-publish setelah tanggal ini. '
                                      'Kosongkan untuk langsung aktif.')
    end_date = fields.Datetime(string='End Date',
                               help='Auto-unpublish setelah tanggal ini. '
                                    'Kosongkan untuk tanpa expiry.')

    api_key_id = fields.Many2one('carousel.api.key', string='Created/Updated by API Key',
                                 readonly=True)
    create_date = fields.Datetime(string='Created', readonly=True)
    write_date = fields.Datetime(string='Last Updated', readonly=True)

    def _is_currently_active(self):
        """Check if slide should be visible based on active flag + schedule."""
        self.ensure_one()
        if not self.active:
            return False
        now = fields.Datetime.now()
        if self.start_date and now < self.start_date:
            return False
        if self.end_date and now > self.end_date:
            return False
        return True

    def toggle_active(self):
        """Toggle active state (called from form view buttons)."""
        for rec in self:
            rec.active = not rec.active

    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        for rec in self:
            if rec.start_date and rec.end_date and rec.start_date > rec.end_date:
                raise ValidationError(_('Start Date must be before End Date.'))

    def to_dict(self):
        """Serialize slide to dict for API response."""
        self.ensure_one()
        base_url = self.env['ir.config_parameter'].sudo().get_param(
            'web.base.url', '')
        return {
            'id': self.id,
            'title': self.title,
            'subtitle': self.subtitle or '',
            'cta_text': self.cta_text or '',
            'link_url': self.link_url or '',
            'image_desktop_url': f'{base_url}/carousel/image/{self.id}/desktop' if self.image_desktop else '',
            'image_mobile_url': f'{base_url}/carousel/image/{self.id}/mobile' if self.image_mobile else '',
            'sequence': self.sequence,
            'active': self.active,
            'is_visible': self._is_currently_active(),
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'create_date': self.create_date.isoformat() if self.create_date else None,
            'write_date': self.write_date.isoformat() if self.write_date else None,
        }
