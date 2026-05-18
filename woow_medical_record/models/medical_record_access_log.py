# Part of Woow Medical. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class MedicalRecordAccessLog(models.Model):
    """Immutable audit log for medical record access and state changes."""

    _name = 'medical.record.access.log'
    _description = 'Medical Record Access Log'
    _order = 'create_date desc'

    record_id = fields.Many2one(
        'medical.record',
        string='Medical Record',
        required=True,
        ondelete='cascade',
        index=True,
        help='The medical record this log entry belongs to.',
    )
    user_id = fields.Many2one(
        'res.users',
        string='User',
        required=True,
        default=lambda self: self.env.user,
        help='User who performed the action.',
    )
    action = fields.Selection(
        selection=[
            ('view', 'View'),
            ('write', 'Write'),
            ('sign', 'Sign'),
            ('unsign', 'Unsign'),
        ],
        string='Action',
        required=True,
        help='Type of access or action performed.',
    )
    note = fields.Char(
        string='Note',
        help='Additional detail about the action.',
    )

    # ------------------------------------------------------------------
    # Immutability enforcement
    # ------------------------------------------------------------------

    def write(self, vals):
        """Prevent modification of audit log entries."""
        raise UserError(
            _('Audit log entries cannot be modified.')
        )

    @api.ondelete(at_uninstall=False)
    def _check_unlink(self):
        """Prevent deletion of audit log entries (except during module uninstall)."""
        raise UserError(
            _('Audit log entries cannot be deleted.')
        )
