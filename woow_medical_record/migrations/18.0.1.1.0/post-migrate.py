# Part of Woow Medical. See LICENSE file for full copyright and licensing details.

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Backfill physician_id for historical records that have NULL values.

    After adding @api.constrains('physician_id'), existing NULL records
    would block any write() on those records. This migration assigns
    the first physician found in the same company, or the first physician
    overall as a fallback.
    """
    # Find how many NULL records exist
    cr.execute(
        "SELECT COUNT(*) FROM medical_record WHERE physician_id IS NULL"
    )
    null_count = cr.fetchone()[0]
    if not null_count:
        _logger.info("No medical records with NULL physician_id. Skipping.")
        return

    _logger.info(
        "Backfilling physician_id for %d medical records...", null_count
    )

    # Assign physician from the same company where possible
    cr.execute("""
        UPDATE medical_record mr
        SET physician_id = (
            SELECT mp.id
            FROM medical_physician mp
            WHERE mp.company_id = mr.company_id
            ORDER BY mp.id
            LIMIT 1
        )
        WHERE mr.physician_id IS NULL
          AND EXISTS (
              SELECT 1 FROM medical_physician mp
              WHERE mp.company_id = mr.company_id
          )
    """)
    updated_same_company = cr.rowcount
    _logger.info(
        "  %d records updated with same-company physician.", updated_same_company
    )

    # Fallback: assign any physician for remaining records
    cr.execute("""
        UPDATE medical_record mr
        SET physician_id = (
            SELECT mp.id FROM medical_physician mp ORDER BY mp.id LIMIT 1
        )
        WHERE mr.physician_id IS NULL
    """)
    updated_fallback = cr.rowcount
    if updated_fallback:
        _logger.info(
            "  %d records updated with fallback physician.", updated_fallback
        )

    _logger.info("physician_id backfill complete.")
