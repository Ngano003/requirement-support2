import pandas as pd
from typing import List
from src.domain.models import Defect


class ResultPresenter:
    def present_defects(self, defects: List[Defect]) -> pd.DataFrame:
        data = []
        for d in defects:
            data.append(
                {
                    "ID": d.id,
                    "Category": d.category.value,
                    "Severity": d.severity.value,
                    "Location": d.location,
                    "Description": d.description,
                    "Recommendation": d.recommendation,
                }
            )
        return pd.DataFrame(data)
