"""
Reference-range registry for fertility-relevant biomarkers.

Each entry records the analyte name, SI unit, sex-specific reference ranges,
and a short description of why the biomarker matters for reproductive health.
These values are used by swarm_5 (analyser) and swarm_6 (bloodwork curator)
when interpreting uploaded lab results.

Notes
-----
* Ranges represent commonly cited *adult* reference intervals and are
  intentionally conservative.  A qualified nutritionist reviews every result
  before it reaches the user.
* ``male_range_min`` / ``male_range_max`` are provided for completeness but
  the current product focuses on female fertility.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class BiomarkerSpec:
    """Specification for a single biomarker.

    Attributes:
        name:                Human-readable biomarker name.
        unit:                Measurement unit (e.g. "ng/mL", "mIU/mL").
        female_range_min:    Lower bound of the female reference range.
        female_range_max:    Upper bound of the female reference range.
        male_range_min:      Lower bound of the male reference range (if applicable).
        male_range_max:      Upper bound of the male reference range (if applicable).
        fertility_relevance: Plain-language explanation of why this analyte matters
                             for fertility.
    """

    name: str
    unit: str
    female_range_min: float
    female_range_max: float
    male_range_min: Optional[float]
    male_range_max: Optional[float]
    fertility_relevance: str


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

BIOMARKER_REGISTRY: dict[str, BiomarkerSpec] = {
    "AMH": BiomarkerSpec(
        name="Anti-Mullerian Hormone",
        unit="ng/mL",
        female_range_min=1.0,
        female_range_max=3.5,
        male_range_min=1.5,
        male_range_max=4.3,
        fertility_relevance=(
            "Reflects ovarian reserve — the number of remaining eggs. Low AMH may "
            "indicate diminished reserve, while very high AMH can suggest PCOS."
        ),
    ),
    "FSH": BiomarkerSpec(
        name="Follicle-Stimulating Hormone",
        unit="mIU/mL",
        female_range_min=3.5,
        female_range_max=12.5,
        male_range_min=1.5,
        male_range_max=12.4,
        fertility_relevance=(
            "Drives follicular development. Elevated day-3 FSH suggests the brain is "
            "working harder to stimulate the ovaries, often a sign of declining reserve."
        ),
    ),
    "LH": BiomarkerSpec(
        name="Luteinizing Hormone",
        unit="mIU/mL",
        female_range_min=2.4,
        female_range_max=12.6,
        male_range_min=1.7,
        male_range_max=8.6,
        fertility_relevance=(
            "Triggers ovulation mid-cycle. An elevated LH-to-FSH ratio is a classic "
            "marker for PCOS and can impair egg release."
        ),
    ),
    "ESTRADIOL": BiomarkerSpec(
        name="Estradiol (E2)",
        unit="pg/mL",
        female_range_min=15.0,
        female_range_max=350.0,
        male_range_min=10.0,
        male_range_max=40.0,
        fertility_relevance=(
            "The primary estrogen. Day-3 estradiol helps assess ovarian function; "
            "elevated levels early in the cycle may mask high FSH and indicate poor reserve."
        ),
    ),
    "PROGESTERONE": BiomarkerSpec(
        name="Progesterone",
        unit="ng/mL",
        female_range_min=5.0,
        female_range_max=20.0,
        male_range_min=0.2,
        male_range_max=1.4,
        fertility_relevance=(
            "Essential for endometrial preparation and maintaining early pregnancy. "
            "Low luteal-phase progesterone can indicate anovulation or luteal-phase defect."
        ),
    ),
    "TSH": BiomarkerSpec(
        name="Thyroid-Stimulating Hormone",
        unit="mIU/L",
        female_range_min=0.4,
        female_range_max=4.0,
        male_range_min=0.4,
        male_range_max=4.0,
        fertility_relevance=(
            "Thyroid dysfunction disrupts menstrual regularity, ovulation, and implantation. "
            "Many reproductive endocrinologists target TSH < 2.5 for conception."
        ),
    ),
    "FREE_T4": BiomarkerSpec(
        name="Free Thyroxine (Free T4)",
        unit="ng/dL",
        female_range_min=0.8,
        female_range_max=1.8,
        male_range_min=0.8,
        male_range_max=1.8,
        fertility_relevance=(
            "Measures active thyroid hormone. Abnormal Free T4 alongside TSH changes "
            "helps distinguish hypothyroidism from hyperthyroidism, both of which affect fertility."
        ),
    ),
    "PROLACTIN": BiomarkerSpec(
        name="Prolactin",
        unit="ng/mL",
        female_range_min=2.0,
        female_range_max=29.0,
        male_range_min=2.0,
        male_range_max=18.0,
        fertility_relevance=(
            "Elevated prolactin (hyperprolactinemia) suppresses GnRH, leading to "
            "irregular periods and anovulation."
        ),
    ),
    "TESTOSTERONE_TOTAL": BiomarkerSpec(
        name="Testosterone (Total)",
        unit="ng/dL",
        female_range_min=15.0,
        female_range_max=70.0,
        male_range_min=264.0,
        male_range_max=916.0,
        fertility_relevance=(
            "Excess testosterone in women is associated with PCOS and can impair "
            "ovulation. In men, low testosterone affects sperm production."
        ),
    ),
    "DHEA_S": BiomarkerSpec(
        name="Dehydroepiandrosterone Sulfate (DHEA-S)",
        unit="mcg/dL",
        female_range_min=35.0,
        female_range_max=430.0,
        male_range_min=80.0,
        male_range_max=560.0,
        fertility_relevance=(
            "An adrenal androgen precursor. Elevated DHEA-S can contribute to "
            "hyperandrogenism and is sometimes supplemented to support egg quality."
        ),
    ),
    "VITAMIN_D": BiomarkerSpec(
        name="Vitamin D (25-OH)",
        unit="ng/mL",
        female_range_min=30.0,
        female_range_max=100.0,
        male_range_min=30.0,
        male_range_max=100.0,
        fertility_relevance=(
            "Vitamin D receptors exist in the ovaries, uterus, and placenta. Deficiency "
            "is linked to lower IVF success rates and pregnancy complications."
        ),
    ),
    "FERRITIN": BiomarkerSpec(
        name="Iron / Ferritin",
        unit="ng/mL",
        female_range_min=20.0,
        female_range_max=200.0,
        male_range_min=30.0,
        male_range_max=400.0,
        fertility_relevance=(
            "Iron stores support oxygen delivery to reproductive tissues. Low ferritin "
            "is common in menstruating women and may impair ovulatory function."
        ),
    ),
    "B12": BiomarkerSpec(
        name="Vitamin B12",
        unit="pg/mL",
        female_range_min=200.0,
        female_range_max=900.0,
        male_range_min=200.0,
        male_range_max=900.0,
        fertility_relevance=(
            "Critical for DNA synthesis and methylation. Deficiency is associated with "
            "anovulation, implantation failure, and recurrent miscarriage."
        ),
    ),
    "FOLATE": BiomarkerSpec(
        name="Folate (Serum)",
        unit="ng/mL",
        female_range_min=3.0,
        female_range_max=20.0,
        male_range_min=3.0,
        male_range_max=20.0,
        fertility_relevance=(
            "Essential for neural-tube development and healthy cell division. Adequate "
            "folate before conception significantly reduces birth defect risk."
        ),
    ),
    "HOMOCYSTEINE": BiomarkerSpec(
        name="Homocysteine",
        unit="umol/L",
        female_range_min=4.0,
        female_range_max=15.0,
        male_range_min=4.0,
        male_range_max=15.0,
        fertility_relevance=(
            "Elevated homocysteine indicates impaired methylation and is linked to "
            "recurrent pregnancy loss, pre-eclampsia, and poor egg quality."
        ),
    ),
    "INSULIN": BiomarkerSpec(
        name="Fasting Insulin",
        unit="uIU/mL",
        female_range_min=2.0,
        female_range_max=25.0,
        male_range_min=2.0,
        male_range_max=25.0,
        fertility_relevance=(
            "Insulin resistance drives excess androgen production and is a root cause "
            "of PCOS-related anovulation."
        ),
    ),
    "GLUCOSE": BiomarkerSpec(
        name="Fasting Glucose",
        unit="mg/dL",
        female_range_min=70.0,
        female_range_max=100.0,
        male_range_min=70.0,
        male_range_max=100.0,
        fertility_relevance=(
            "Chronic hyperglycaemia impairs endometrial receptivity and embryo "
            "development. Glucose management is key in PCOS-related infertility."
        ),
    ),
    "HBA1C": BiomarkerSpec(
        name="Haemoglobin A1c",
        unit="%",
        female_range_min=4.0,
        female_range_max=5.6,
        male_range_min=4.0,
        male_range_max=5.6,
        fertility_relevance=(
            "Reflects average blood sugar over ~3 months. Pre-conception HbA1c control "
            "reduces the risk of congenital anomalies and miscarriage."
        ),
    ),
    "CRP": BiomarkerSpec(
        name="C-Reactive Protein (hs-CRP)",
        unit="mg/L",
        female_range_min=0.0,
        female_range_max=3.0,
        male_range_min=0.0,
        male_range_max=3.0,
        fertility_relevance=(
            "A marker of systemic inflammation. Chronic low-grade inflammation can "
            "impair implantation, and elevated CRP is seen in endometriosis and PCOS."
        ),
    ),
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_biomarker(key: str) -> BiomarkerSpec | None:
    """Look up a biomarker by its registry key (case-insensitive).

    Returns ``None`` if the key is not recognised.
    """
    return BIOMARKER_REGISTRY.get(key.upper().replace(" ", "_"))


def list_biomarker_names() -> list[str]:
    """Return a sorted list of all registered biomarker display names."""
    return sorted(spec.name for spec in BIOMARKER_REGISTRY.values())


def is_in_range(
    key: str,
    value: float,
    *,
    sex: str = "female",
) -> bool | None:
    """Check whether *value* falls within the reference range for the given *sex*.

    Args:
        key:   Registry key (e.g. ``"AMH"``, ``"TSH"``).
        value: The measured value.
        sex:   ``"female"`` or ``"male"``.

    Returns:
        ``True`` if within range, ``False`` if outside, or ``None`` if the
        biomarker key is not recognised.
    """
    spec = get_biomarker(key)
    if spec is None:
        return None

    if sex == "male":
        if spec.male_range_min is None or spec.male_range_max is None:
            return None
        return spec.male_range_min <= value <= spec.male_range_max

    return spec.female_range_min <= value <= spec.female_range_max
