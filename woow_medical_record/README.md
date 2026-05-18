# Woow 醫療 - 病歷管理 (woow_medical_record)

## Overview

Odoo 18 module for managing aesthetic clinic medical records using SOAP documentation.

## Features

- SOAP medical records (Subjective, Objective, Assessment, Plan)
- Vital signs tracking (height, weight, BP, pulse, temperature)
- Daily auto-numbering (YYYYMMDD-001) with date range sequence
- Three-state workflow: Draft -> In Progress -> Signed
- Signing validation (at least one SOAP field required)
- Reset to draft with audit trail
- Immutable access audit log
- File attachments (before/after photos, lab reports)
- Calendar and pivot views
- Extends patient module with record count stat button

## Security

| Group | medical.record | access.log |
|-------|---------------|------------|
| Medical User | Read only | Create only |
| Medical Physician | Read, write, create | Create only |
| Medical Admin | Read, write, create | Read, create |

Record rules:
- Physicians see only their own records
- Admins see all company records
- Multi-company isolation via global rule

## Dependencies

- `woow_medical_patient`
- `mail`

## Installation

1. Install `woow_medical_patient` first
2. Copy `woow_medical_record` to your Odoo addons path
3. Update module list and install "Woow 醫療 - 病歷管理"

## License

LGPL-3

## Author

WoowTech — https://www.woowtech.io
