# Part of Woow Medical. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class MedicalSpecialty(models.Model):
    """Medical Specialty — categorises physicians by clinical discipline."""

    _name = 'medical.specialty'
    _description = 'Medical Specialty'
    _order = 'name'

    name = fields.Char(
        string='Specialty Name',
        required=True,
        translate=True,
    )
    code = fields.Char(
        string='Code',
        help='Short code for the specialty.',
    )
    active = fields.Boolean(
        default=True,
    )
