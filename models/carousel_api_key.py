# -*- coding: utf-8 -*-
import secrets
import logging
from odoo import fields, models, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# API key prefix for easy identification
API_KEY_PREFIX = 'wlc_'  # Warung Lakku Carousel

# Scope definitions
SCOPE_READ = 'read'      # GET /carousel/api/slides
SCOPE_WRITE = 'write'    # POST, PUT, DELETE /carousel/api/slides
SCOPE_ADMIN = 'admin'    # All above + generate/revoke API keys

SCOPE_SELECTION = [
    (SCOPE_READ, 'Read (GET slides only)'),
    (SCOPE_WRITE, 'Write (GET/POST/PUT/DELETE slides)'),
    (SCOPE_ADMIN, 'Admin (all + API key management)'),
]


class CarouselApiKey(models.Model):
    _name = 'carousel.api.key'
    _description = 'Carousel API Key'
    _order = 'create_date desc'
    _rec_name = 'name'

    name = fields.Char(string='Label', required=True,
                       help='Human-readable label for this API key '
                            '(e.g. "n8n workflow", "Mobile app")')
    key = fields.Char(string='API Key', readonly=True, copy=False,
                      help='The actual API key. Only shown once at creation.')
    scope = fields.Selection(SCOPE_SELECTION, string='Scope',
                             default=SCOPE_WRITE, required=True)
    active = fields.Boolean(string='Active', default=True)
    expires_at = fields.Datetime(string='Expires At',
                                 help='Auto-revoke after this date. '
                                      'Leave empty for no expiry.')
    last_used = fields.Datetime(string='Last Used', readonly=True)
    use_count = fields.Integer(string='Use Count', readonly=True, default=0)

    created_by = fields.Many2one('res.users', string='Created By',
                                 default=lambda self: self.env.user, readonly=True)
    create_date = fields.Datetime(string='Created', readonly=True)

    _sql_constraints = [
        ('unique_key', 'UNIQUE(key)', 'API Key must be unique.'),
    ]

    @api.model
    def generate_key(self, name, scope=SCOPE_WRITE, expires_at=None):
        """Generate a new API key. Returns the key string (only shown once)."""
        # Generate cryptographically secure random key
        raw = secrets.token_urlsafe(32)
        key = f'{API_KEY_PREFIX}{raw}'
        record = self.create({
            'name': name,
            'key': key,
            'scope': scope,
            'expires_at': expires_at,
        })
        _logger.info('Carousel API key created: %s (scope=%s, id=%d)',
                     name, scope, record.id)
        return record, key

    def revoke(self):
        """Revoke (deactivate) API keys."""
        for rec in self:
            rec.active = False
            _logger.info('Carousel API key revoked: %s (id=%d)', rec.name, rec.id)

    @api.model
    def validate_key(self, key, required_scope=None):
        """Validate an API key and return the record if valid.
        
        Args:
            key: The API key string from Authorization header
            required_scope: Minimum scope required ('read', 'write', or 'admin')
            
        Returns:
            carousel.api.key recordset if valid, empty recordset if invalid
        """
        if not key:
            return self.env['carousel.api.key']
        
        # Strip "Bearer " prefix if present
        if key.startswith('Bearer '):
            key = key[7:]
        
        # Find the key
        record = self.search([('key', '=', key), ('active', '=', True)], limit=1)
        if not record:
            return self.env['carousel.api.key']
        
        # Check expiry
        if record.expires_at and record.expires_at < fields.Datetime.now():
            return self.env['carousel.api.key']
        
        # Check scope
        if required_scope:
            scope_hierarchy = {SCOPE_READ: 1, SCOPE_WRITE: 2, SCOPE_ADMIN: 3}
            if scope_hierarchy.get(record.scope, 0) < scope_hierarchy.get(required_scope, 0):
                return self.env['carousel.api.key']
        
        # Update usage tracking
        record.sudo().write({
            'last_used': fields.Datetime.now(),
            'use_count': record.use_count + 1,
        })
        
        return record

    def to_dict(self):
        """Serialize for API response (never expose the actual key)."""
        self.ensure_one()
        return {
            'id': self.id,
            'name': self.name,
            'scope': self.scope,
            'active': self.active,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'last_used': self.last_used.isoformat() if self.last_used else None,
            'use_count': self.use_count,
            'created_by': self.created_by.name if self.created_by else '',
            'create_date': self.create_date.isoformat() if self.create_date else None,
            # Note: 'key' is intentionally NOT included for security
            'key_preview': f'{self.key[:12]}...{self.key[-4:]}' if self.key else '',
        }
