# Part of Woow Medical. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # --- Reverse link from medical.physician ---
    physician_ids = fields.One2many(
        'medical.physician',
        'partner_id',
        string='Physicians',
        help='Physician profiles linked to this contact.',
    )
    physician_count = fields.Integer(
        string='Physician Count',
        compute='_compute_physician_count',
    )

    @api.depends('physician_ids')
    def _compute_physician_count(self):
        physician_data = self.env['medical.physician'].sudo().read_group(
            domain=[('partner_id', 'in', self.ids)],
            fields=['partner_id'],
            groupby=['partner_id'],
        )
        mapped_data = {
            data['partner_id'][0]: data['partner_id_count']
            for data in physician_data
        }
        for partner in self:
            partner.physician_count = mapped_data.get(partner.id, 0)

    def action_open_physicians(self):
        """Open physician profile(s) linked to this partner."""
        self.ensure_one()
        physicians = self.physician_ids
        if len(physicians) == 1:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Physician'),
                'res_model': 'medical.physician',
                'view_mode': 'form',
                'res_id': physicians.id,
            }
        return {
            'type': 'ir.actions.act_window',
            'name': _('Physicians'),
            'res_model': 'medical.physician',
            'view_mode': 'list,form',
            'domain': [('partner_id', '=', self.id)],
        }
