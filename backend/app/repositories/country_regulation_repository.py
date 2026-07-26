"""Country regulation data access."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.telecom import CountryRegulation


class CountryRegulationRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_code(self, country_code: str) -> CountryRegulation | None:
        return (
            self._db.query(CountryRegulation)
            .filter(CountryRegulation.country_code == country_code.upper())
            .first()
        )

    def list_all(self) -> list[CountryRegulation]:
        return self._db.query(CountryRegulation).order_by(CountryRegulation.country_code).all()

    def upsert_seed(self, rows: list[dict]) -> None:
        for row in rows:
            existing = self.get_by_code(row["country_code"])
            if existing:
                for key, value in row.items():
                    if key == "metadata":
                        setattr(existing, "metadata_", value)
                    else:
                        setattr(existing, key, value)
            else:
                self._db.add(
                    CountryRegulation(
                        country_code=row["country_code"],
                        country_name=row["country_name"],
                        requires_end_user=row["requires_end_user"],
                        requires_regulatory_bundle=row["requires_regulatory_bundle"],
                        supports_voice=row["supports_voice"],
                        supports_sms=row["supports_sms"],
                        supports_local_numbers=row["supports_local_numbers"],
                        supports_mobile_numbers=row["supports_mobile_numbers"],
                        supports_toll_free=row["supports_toll_free"],
                        metadata_=row.get("metadata", {}),
                    )
                )
        self._db.commit()
