# Woow 醫療 - 病患管理 (woow_medical_patient)

## Overview

Odoo 18 module for managing aesthetic clinic patient records. One record per patient, lifelong.

## Features

- Patient registration with auto-generated patient number (P000001)
- Delegation inheritance from `res.partner` (shared name, phone, email, address, image)
- PII field protection (national ID, NHI card) via dedicated security group
- Medical history tracking (allergies, chronic diseases, medications, surgeries)
- Emergency contact information
- Multi-company isolation
- Kanban, list, and form views

## Security Groups

| Group | Role | Permissions |
|-------|------|-------------|
| Medical User | Reception, nurses | Read, write, create patients |
| Medical Physician | Doctors | Inherits Medical User |
| Medical Administrator | Full access | Can delete patients |
| Medical PII Access | Independent | View national ID / NHI card fields |

## Dependencies

- `base`
- `contacts`
- `mail`

## Installation

1. Copy `woow_medical_patient` to your Odoo addons path
2. Update the module list: Settings > Apps > Update Apps List
3. Install "Woow 醫療 - 病患管理"

## License

LGPL-3

## Author

WoowTech — https://www.woowtech.io
