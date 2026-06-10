# Part of Woow Medical. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class MedicalPhysicianRecord(models.Model):
    """Extend medical.physician with record-related fields."""

    _inherit = 'medical.physician'

    record_ids = fields.One2many(
        'medical.record',
        'physician_id',
        string='Medical Records',
        help='All medical records by this physician.',
    )
    record_count = fields.Integer(
        string='Record Count',
        compute='_compute_record_count',
        help='Number of medical records.',
    )

    @api.depends('record_ids')
    def _compute_record_count(self):
        """Compute the number of medical records for each physician."""
        if not self.ids:
            for physician in self:
                physician.record_count = 0
            return
        data = self.env['medical.record'].sudo().read_group(
            [('physician_id', 'in', self.ids)],
            ['physician_id'],
            ['physician_id'],
        )
        counts = {d['physician_id'][0]: d['physician_id_count'] for d in data}
        for physician in self:
            physician.record_count = counts.get(physician.id, 0)

    def action_view_records(self):
        """Open medical records for this physician."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Medical Records'),
            'res_model': 'medical.record',
            'view_mode': 'list,form',
            'domain': [('physician_id', '=', self.id)],
            'context': {'default_physician_id': self.id, 'medical_form_view': True},
        }
