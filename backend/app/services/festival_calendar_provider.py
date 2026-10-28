import abc
from datetime import date, timedelta
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass

class FestivalCalculationType:
    FIXED_GREGORIAN = "FIXED_GREGORIAN"          # Fixed month & day (e.g., Christmas Dec 25)
    RULE_BASED_GREGORIAN = "RULE_BASED_GREGORIAN" # Gregorian rule (e.g., 4th Thursday of Nov)
    LUNISOLAR_ASTRONOMICAL = "LUNISOLAR_ASTRONOMICAL" # Lunisolar calendar (e.g., Diwali, Holi, Easter)
    ISLAMIC_LUNAR = "ISLAMIC_LUNAR"              # Pure lunar, sighting-dependent (e.g., Eid)

@dataclass
class SuggestedFestivalItem:
    name: str
    slug: str
    country_code: str
    region: Optional[str]
    category_group: str
    calculation_type: str
    year: int
    start_date: date
    end_date: date
    prep_start_date: date
    prep_deadline_date: date
    season_comparison_start: date
    season_comparison_end: date
    date_status: str       # UNVERIFIED, ESTIMATED, CONFIRMED
    approval_status: str   # Always PENDING for suggestions
    description: str
    notes: Optional[str] = None

class BaseFestivalCalendarProvider(abc.ABC):
    """
    Abstract interface for calendar data providers.
    Allows replacing or augmenting the default static astronomical registry
    with third-party calendar or government holiday APIs in the future.
    """

    @abc.abstractmethod
    def get_supported_countries(self) -> List[Dict[str, str]]:
        """Return list of supported countries with ISO codes."""
        pass

    @abc.abstractmethod
    def suggest_festivals(self, country_code: str, year: int) -> List[SuggestedFestivalItem]:
        """Generate festival suggestions for a country and year."""
        pass

    @abc.abstractmethod
    def get_festival_dates(self, slug: str, country_code: str, year: int) -> Optional[SuggestedFestivalItem]:
        """Fetch dates for a specific festival edition."""
        pass


def compute_easter(year: int) -> date:
    """
    Computus algorithm (Meeus/Jones/Butcher algorithm) to compute Western Easter Sunday.
    Scientifically accurate for any Gregorian year.
    """
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)

def compute_nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    """
    Computes the nth weekday of a given month (0=Monday, 6=Sunday).
    Example: 4th Thursday in November -> month=11, weekday=3, n=4.
    """
    first_day = date(year, month, 1)
    first_weekday = first_day.weekday()
    day_offset = (weekday - first_weekday) % 7
    day = 1 + day_offset + (n - 1) * 7
    return date(year, month, day)


class StaticRegistryCalendarProvider(BaseFestivalCalendarProvider):
    """
    Default production-safe calendar provider.
    Uses verified historical/astronomical date tables for lunisolar festivals (2024-2026),
    rule-based Gregorian formulas for holidays like Thanksgiving/Easter,
    and fixed Gregorian dates for holidays like Christmas/Halloween.
    If a lunar date cannot be verified for distant years, it marks the status UNVERIFIED.
    """

    SUPPORTED_COUNTRIES = [
        {"code": "IN", "name": "India"},
        {"code": "US", "name": "United States"},
        {"code": "GB", "name": "United Kingdom"},
        {"code": "CA", "name": "Canada"},
        {"code": "AU", "name": "Australia"},
        {"code": "AE", "name": "United Arab Emirates"},
    ]

    # Verified Lunisolar Dates for Hindu & Islamic Festivals (2024 - 2026)
    # Beyond 2026, lunisolar dates are marked UNVERIFIED with estimated fallback
    VERIFIED_LUNAR_TABLE: Dict[Tuple[str, int], Tuple[date, date, str, str]] = {
        # (slug, year): (start_date, end_date, date_status, notes)
        # India (Hindu Lunisolar)
        ("diwali", 2024): (date(2024, 11, 1), date(2024, 11, 3), "CONFIRMED", "Amavasya Tithi (Lakshmi Puja)"),
        ("diwali", 2025): (date(2025, 10, 20), date(2025, 10, 22), "CONFIRMED", "Kartik Amavasya"),
        ("diwali", 2026): (date(2026, 11, 8), date(2026, 11, 10), "CONFIRMED", "Kartik Amavasya"),

        ("holi", 2024): (date(2024, 3, 25), date(2024, 3, 26), "CONFIRMED", "Phalguna Purnima"),
        ("holi", 2025): (date(2025, 3, 14), date(2025, 3, 15), "CONFIRMED", "Phalguna Purnima"),
        ("holi", 2026): (date(2026, 3, 4), date(2026, 3, 5), "CONFIRMED", "Phalguna Purnima"),

        ("navratri", 2024): (date(2024, 10, 3), date(2024, 10, 12), "CONFIRMED", "Sharad Navratri 9 days"),
        ("navratri", 2025): (date(2025, 9, 22), date(2025, 10, 1), "CONFIRMED", "Sharad Navratri 9 days"),
        ("navratri", 2026): (date(2026, 10, 11), date(2026, 10, 20), "CONFIRMED", "Sharad Navratri 9 days"),

        ("raksha-bandhan", 2024): (date(2024, 8, 19), date(2024, 8, 19), "CONFIRMED", "Shravana Purnima"),
        ("raksha-bandhan", 2025): (date(2025, 8, 9), date(2025, 8, 9), "CONFIRMED", "Shravana Purnima"),
        ("raksha-bandhan", 2026): (date(2026, 8, 28), date(2026, 8, 28), "CONFIRMED", "Shravana Purnima"),

        ("janmashtami", 2024): (date(2024, 8, 26), date(2024, 8, 26), "CONFIRMED", "Krishna Janmashtami"),
        ("janmashtami", 2025): (date(2025, 8, 16), date(2025, 8, 16), "CONFIRMED", "Krishna Janmashtami"),
        ("janmashtami", 2026): (date(2026, 9, 4), date(2026, 9, 4), "CONFIRMED", "Krishna Janmashtami"),

        ("ganesh-chaturthi", 2024): (date(2024, 9, 7), date(2024, 9, 17), "CONFIRMED", "Vinayaka Chaturthi 10 days"),
        ("ganesh-chaturthi", 2025): (date(2025, 8, 27), date(2025, 9, 6), "CONFIRMED", "Vinayaka Chaturthi 10 days"),
        ("ganesh-chaturthi", 2026): (date(2026, 9, 14), date(2026, 9, 24), "CONFIRMED", "Vinayaka Chaturthi 10 days"),

        # UAE (Islamic Lunar Calendar - Subject to moon sighting)
        ("eid-al-fitr", 2024): (date(2024, 4, 10), date(2024, 4, 12), "CONFIRMED", "Shawwal 1-3 (Subject to sighting)"),
        ("eid-al-fitr", 2025): (date(2025, 3, 31), date(2025, 4, 2), "ESTIMATED", "Astronomical projection; subject to moon sighting"),
        ("eid-al-fitr", 2026): (date(2026, 3, 20), date(2026, 3, 22), "ESTIMATED", "Astronomical projection; subject to moon sighting"),

        ("eid-al-adha", 2024): (date(2024, 6, 16), date(2024, 6, 19), "CONFIRMED", "Dhu al-Hijjah 10-13"),
        ("eid-al-adha", 2025): (date(2025, 6, 6), date(2025, 6, 9), "ESTIMATED", "Astronomical projection; subject to moon sighting"),
        ("eid-al-adha", 2026): (date(2026, 5, 27), date(2026, 5, 30), "ESTIMATED", "Astronomical projection; subject to moon sighting"),
    }

    def get_supported_countries(self) -> List[Dict[str, str]]:
        return self.SUPPORTED_COUNTRIES

    def _normalize_country(self, code: str) -> str:
        c = (code or "").strip().upper()
        return "GB" if c == "UK" else c

    def suggest_festivals(self, country_code: str, year: int) -> List[SuggestedFestivalItem]:
        c = self._normalize_country(country_code)
        suggestions: List[SuggestedFestivalItem] = []

        if c == "IN":
            suggestions.extend(self._get_india_festivals(year))
        elif c == "US":
            suggestions.extend(self._get_usa_festivals(year))
        elif c == "GB":
            suggestions.extend(self._get_uk_festivals(year))
        elif c == "CA":
            suggestions.extend(self._get_canada_festivals(year))
        elif c == "AU":
            suggestions.extend(self._get_australia_festivals(year))
        elif c == "AE":
            suggestions.extend(self._get_uae_festivals(year))

        return suggestions

    def get_festival_dates(self, slug: str, country_code: str, year: int) -> Optional[SuggestedFestivalItem]:
        all_festivals = self.suggest_festivals(country_code, year)
        for f in all_festivals:
            if f.slug == slug:
                return f
        return None

    def _build_item(
        self,
        name: str,
        slug: str,
        country_code: str,
        region: Optional[str],
        category_group: str,
        calc_type: str,
        year: int,
        start_date: date,
        end_date: date,
        date_status: str,
        description: str,
        prep_days: int = 45,
        deadline_days: int = 15,
        notes: Optional[str] = None
    ) -> SuggestedFestivalItem:
        prep_start = start_date - timedelta(days=prep_days)
        prep_deadline = start_date - timedelta(days=deadline_days)
        comp_start = start_date - timedelta(days=prep_days)
        comp_end = end_date + timedelta(days=2)

        return SuggestedFestivalItem(
            name=name,
            slug=slug,
            country_code=country_code,
            region=region,
            category_group=category_group,
            calculation_type=calc_type,
            year=year,
            start_date=start_date,
            end_date=end_date,
            prep_start_date=prep_start,
            prep_deadline_date=prep_deadline,
            season_comparison_start=comp_start,
            season_comparison_end=comp_end,
            date_status=date_status,
            approval_status="PENDING",  # Always PENDING for suggestions
            description=description,
            notes=notes
        )

    # ------------------ COUNTRY SPECIFIC REGISTRIES ------------------
    def _get_india_festivals(self, year: int) -> List[SuggestedFestivalItem]:
        items = []

        # 1. Makar Sankranti (Solar Hindu - Jan 14 fixed)
        items.append(self._build_item(
            name="Makar Sankranti",
            slug="makar-sankranti",
            country_code="IN",
            region="National / Gujarat / Maharashtra",
            category_group="Cultural & Harvest",
            calc_type=FestivalCalculationType.FIXED_GREGORIAN,
            year=year,
            start_date=date(year, 1, 14),
            end_date=date(year, 1, 15),
            date_status="CONFIRMED",
            description="Major harvest festival and kite flying celebration across India."
        ))

        # 2-7. Lunisolar Hindu festivals
        lunar_configs = [
            ("Diwali", "diwali", "National", "Major Religious & Cultural", "Festival of Lights — peak commercial & shopping season.", 60, 15),
            ("Holi", "holi", "National", "Cultural & Spring", "Festival of Colors — cards, posters, and party banners.", 40, 10),
            ("Navratri", "navratri", "Gujarat / Maharashtra / National", "Religious & Folk Dance", "9-night Garba festival — heavy creative asset demand.", 45, 12),
            ("Raksha Bandhan", "raksha-bandhan", "National", "Cultural", "Celebration of sibling bonds — personalized cards and banners.", 35, 7),
            ("Krishna Janmashtami", "janmashtami", "National", "Religious", "Birth of Lord Krishna — greeting templates and status videos.", 30, 7),
            ("Ganesh Chaturthi", "ganesh-chaturthi", "Maharashtra / National", "Religious & Cultural", "10-day celebration of Lord Ganesha.", 40, 10),
        ]

        for name, slug, region, group, desc, prep, dead in lunar_configs:
            lookup = self.VERIFIED_LUNAR_TABLE.get((slug, year))
            if lookup:
                s_date, e_date, status, notes = lookup
            else:
                # Distant year fallback: must be UNVERIFIED
                s_date = date(year, 10, 15)
                e_date = date(year, 10, 17)
                status = "UNVERIFIED"
                notes = "Future lunisolar date not yet published in Hindu Panchang table. Requires Manager verification."

            items.append(self._build_item(
                name=name,
                slug=slug,
                country_code="IN",
                region=region,
                category_group=group,
                calc_type=FestivalCalculationType.LUNISOLAR_ASTRONOMICAL,
                year=year,
                start_date=s_date,
                end_date=e_date,
                date_status=status,
                description=desc,
                prep_days=prep,
                deadline_days=dead,
                notes=notes
            ))

        return items

    def _get_usa_festivals(self, year: int) -> List[SuggestedFestivalItem]:
        items = []

        # 1. Valentine's Day (Feb 14 fixed)
        items.append(self._build_item(
            name="Valentine's Day",
            slug="valentines-day",
            country_code="US",
            region="National",
            category_group="Commercial & Romance",
            calc_type=FestivalCalculationType.FIXED_GREGORIAN,
            year=year,
            start_date=date(year, 2, 14),
            end_date=date(year, 2, 14),
            date_status="CONFIRMED",
            description="Major romantic gift, card, and social media celebration.",
            prep_days=30,
            deadline_days=7
        ))

        # 2. Independence Day (July 4 fixed)
        items.append(self._build_item(
            name="Independence Day",
            slug="independence-day-us",
            country_code="US",
            region="National",
            category_group="National & Patriotism",
            calc_type=FestivalCalculationType.FIXED_GREGORIAN,
            year=year,
            start_date=date(year, 7, 4),
            end_date=date(year, 7, 4),
            date_status="CONFIRMED",
            description="4th of July patriotic banners, BBQ flyers, and party invitations.",
            prep_days=35,
            deadline_days=7
        ))

        # 3. Halloween (Oct 31 fixed)
        items.append(self._build_item(
            name="Halloween",
            slug="halloween",
            country_code="US",
            region="National",
            category_group="Commercial & Cultural",
            calc_type=FestivalCalculationType.FIXED_GREGORIAN,
            year=year,
            start_date=date(year, 10, 31),
            end_date=date(year, 10, 31),
            date_status="CONFIRMED",
            description="Spooky templates, costume party flyers, and social promotions.",
            prep_days=45,
            deadline_days=10
        ))

        # 4. Thanksgiving (4th Thursday in November)
        tg_date = compute_nth_weekday(year, 11, 3, 4)
        items.append(self._build_item(
            name="Thanksgiving",
            slug="thanksgiving-us",
            country_code="US",
            region="National",
            category_group="Family & Gratitude",
            calc_type=FestivalCalculationType.RULE_BASED_GREGORIAN,
            year=year,
            start_date=tg_date,
            end_date=tg_date + timedelta(days=1),
            date_status="CONFIRMED",
            description="Thanksgiving dinner invitations, autumn banners, and Black Friday kickoff.",
            prep_days=40,
            deadline_days=10,
            notes=f"Calculated as 4th Thursday in November ({tg_date.isoformat()})."
        ))

        # 5. Christmas (Dec 25 fixed)
        items.append(self._build_item(
            name="Christmas",
            slug="christmas",
            country_code="US",
            region="National",
            category_group="Religious & Commercial",
            calc_type=FestivalCalculationType.FIXED_GREGORIAN,
            year=year,
            start_date=date(year, 12, 25),
            end_date=date(year, 12, 25),
            date_status="CONFIRMED",
            description="Global holiday shopping and holiday card season.",
            prep_days=60,
            deadline_days=15
        ))

        return items

    def _get_uk_festivals(self, year: int) -> List[SuggestedFestivalItem]:
        items = []

        # 1. Easter (Calculated Computus)
        easter_sunday = compute_easter(year)
        items.append(self._build_item(
            name="Easter",
            slug="easter",
            country_code="GB",
            region="National",
            category_group="Religious & Spring",
            calc_type=FestivalCalculationType.LUNISOLAR_ASTRONOMICAL,
            year=year,
            start_date=easter_sunday - timedelta(days=2),  # Good Friday
            end_date=easter_sunday + timedelta(days=1),    # Easter Monday
            date_status="CONFIRMED",
            description="Easter Sunday egg hunt flyers, church posters, and spring cards.",
            prep_days=35,
            deadline_days=7,
            notes=f"Calculated via Gregorian Computus algorithm: Easter Sunday is {easter_sunday.isoformat()}."
        ))

        # 2. Halloween (Oct 31 fixed)
        items.append(self._build_item(
            name="Halloween",
            slug="halloween-uk",
            country_code="GB",
            region="National",
            category_group="Commercial & Cultural",
            calc_type=FestivalCalculationType.FIXED_GREGORIAN,
            year=year,
            start_date=date(year, 10, 31),
            end_date=date(year, 10, 31),
            date_status="CONFIRMED",
            description="Costume party invitations and pumpkin carving event banners.",
            prep_days=30,
            deadline_days=7
        ))

        # 3. Bonfire Night / Guy Fawkes (Nov 5 fixed)
        items.append(self._build_item(
            name="Bonfire Night",
            slug="bonfire-night",
            country_code="GB",
            region="National (UK)",
            category_group="Cultural & Historical",
            calc_type=FestivalCalculationType.FIXED_GREGORIAN,
            year=year,
            start_date=date(year, 11, 5),
            end_date=date(year, 11, 5),
            date_status="CONFIRMED",
            description="Fireworks display posters and Guy Fawkes night event flyers.",
            prep_days=25,
            deadline_days=5
        ))

        # 4. Christmas (Dec 25 fixed)
        items.append(self._build_item(
            name="Christmas",
            slug="christmas-uk",
            country_code="GB",
            region="National",
            category_group="Religious & Commercial",
            calc_type=FestivalCalculationType.FIXED_GREGORIAN,
            year=year,
            start_date=date(year, 12, 25),
            end_date=date(year, 12, 26),  # Boxing Day
            date_status="CONFIRMED",
            description="Christmas and Boxing Day sales graphics and family greeting cards.",
            prep_days=60,
            deadline_days=15
        ))

        return items

    def _get_canada_festivals(self, year: int) -> List[SuggestedFestivalItem]:
        items = []

        # 1. Canada Day (July 1 fixed)
        items.append(self._build_item(
            name="Canada Day",
            slug="canada-day",
            country_code="CA",
            region="National",
            category_group="National",
            calc_type=FestivalCalculationType.FIXED_GREGORIAN,
            year=year,
            start_date=date(year, 7, 1),
            end_date=date(year, 7, 1),
            date_status="CONFIRMED",
            description="National celebration flyers, maple leaf graphics, and community parade banners.",
            prep_days=35,
            deadline_days=7
        ))

        # 2. Thanksgiving (Canada - 2nd Monday in October)
        ca_tg_date = compute_nth_weekday(year, 10, 0, 2)
        items.append(self._build_item(
            name="Thanksgiving (Canada)",
            slug="thanksgiving-ca",
            country_code="CA",
            region="National",
            category_group="Family & Gratitude",
            calc_type=FestivalCalculationType.RULE_BASED_GREGORIAN,
            year=year,
            start_date=ca_tg_date,
            end_date=ca_tg_date,
            date_status="CONFIRMED",
            description="Canadian Thanksgiving dinner invitations and autumn harvest posters.",
            prep_days=35,
            deadline_days=7,
            notes=f"Calculated as 2nd Monday in October ({ca_tg_date.isoformat()}). Distinct from US Thanksgiving."
        ))

        # 3. Halloween (Oct 31 fixed)
        items.append(self._build_item(
            name="Halloween",
            slug="halloween-ca",
            country_code="CA",
            region="National",
            category_group="Commercial & Cultural",
            calc_type=FestivalCalculationType.FIXED_GREGORIAN,
            year=year,
            start_date=date(year, 10, 31),
            end_date=date(year, 10, 31),
            date_status="CONFIRMED",
            description="Halloween promotional graphics and party invitations."
        ))

        # 4. Christmas (Dec 25 fixed)
        items.append(self._build_item(
            name="Christmas",
            slug="christmas-ca",
            country_code="CA",
            region="National",
            category_group="Religious & Commercial",
            calc_type=FestivalCalculationType.FIXED_GREGORIAN,
            year=year,
            start_date=date(year, 12, 25),
            end_date=date(year, 12, 26),
            date_status="CONFIRMED",
            description="Christmas holiday cards, winter posters, and Boxing Day sale promotions."
        ))

        return items

    def _get_australia_festivals(self, year: int) -> List[SuggestedFestivalItem]:
        items = []

        # 1. Australia Day (Jan 26 fixed)
        items.append(self._build_item(
            name="Australia Day",
            slug="australia-day",
            country_code="AU",
            region="National",
            category_group="National",
            calc_type=FestivalCalculationType.FIXED_GREGORIAN,
            year=year,
            start_date=date(year, 1, 26),
            end_date=date(year, 1, 26),
            date_status="CONFIRMED",
            description="Aussie BBQ invitations, summer beach party flyers, and national day banners.",
            prep_days=30,
            deadline_days=7
        ))

        # 2. Easter (Calculated Computus)
        easter_sunday = compute_easter(year)
        items.append(self._build_item(
            name="Easter",
            slug="easter-au",
            country_code="AU",
            region="National",
            category_group="Religious & Holiday",
            calc_type=FestivalCalculationType.LUNISOLAR_ASTRONOMICAL,
            year=year,
            start_date=easter_sunday - timedelta(days=2),
            end_date=easter_sunday + timedelta(days=1),
            date_status="CONFIRMED",
            description="Easter long weekend sales and family event posters."
        ))

        # 3. Christmas (Dec 25 - Summer in Australia)
        items.append(self._build_item(
            name="Christmas",
            slug="christmas-au",
            country_code="AU",
            region="National",
            category_group="Religious & Commercial",
            calc_type=FestivalCalculationType.FIXED_GREGORIAN,
            year=year,
            start_date=date(year, 12, 25),
            end_date=date(year, 12, 26),
            date_status="CONFIRMED",
            description="Summer Christmas celebration cards, beach party invitations, and holiday sales.",
            prep_days=60,
            deadline_days=15
        ))

        return items

    def _get_uae_festivals(self, year: int) -> List[SuggestedFestivalItem]:
        items = []

        # 1. Eid al-Fitr (Islamic Lunar)
        fitr_lookup = self.VERIFIED_LUNAR_TABLE.get(("eid-al-fitr", year))
        if fitr_lookup:
            f_start, f_end, f_stat, f_notes = fitr_lookup
        else:
            f_start = date(year, 4, 1)
            f_end = date(year, 4, 3)
            f_stat = "UNVERIFIED"
            f_notes = "Unverified future Hijri date; astronomical calculation required."

        items.append(self._build_item(
            name="Eid al-Fitr",
            slug="eid-al-fitr",
            country_code="AE",
            region="Middle East / UAE",
            category_group="Religious & Cultural",
            calc_type=FestivalCalculationType.ISLAMIC_LUNAR,
            year=year,
            start_date=f_start,
            end_date=f_end,
            date_status=f_stat,
            description="End of Ramadan celebration — Eid greeting cards, gold-themed banners, and gift tags.",
            prep_days=45,
            deadline_days=10,
            notes=f_notes
        ))

        # 2. Eid al-Adha (Islamic Lunar)
        adha_lookup = self.VERIFIED_LUNAR_TABLE.get(("eid-al-adha", year))
        if adha_lookup:
            a_start, a_end, a_stat, a_notes = adha_lookup
        else:
            a_start = date(year, 6, 15)
            a_end = date(year, 6, 18)
            a_stat = "UNVERIFIED"
            a_notes = "Unverified future Hijri date; astronomical calculation required."

        items.append(self._build_item(
            name="Eid al-Adha",
            slug="eid-al-adha",
            country_code="AE",
            region="Middle East / UAE",
            category_group="Religious & Cultural",
            calc_type=FestivalCalculationType.ISLAMIC_LUNAR,
            year=year,
            start_date=a_start,
            end_date=a_end,
            date_status=a_stat,
            description="Feast of the Sacrifice celebration — Islamic greeting cards and sacrifice announcements.",
            prep_days=40,
            deadline_days=10,
            notes=a_notes
        ))

        # 3. UAE National Day (Dec 2-3 fixed)
        items.append(self._build_item(
            name="UAE National Day",
            slug="uae-national-day",
            country_code="AE",
            region="United Arab Emirates",
            category_group="National",
            calc_type=FestivalCalculationType.FIXED_GREGORIAN,
            year=year,
            start_date=date(year, 12, 2),
            end_date=date(year, 12, 3),
            date_status="CONFIRMED",
            description="Spirit of the Union celebration — UAE flag banners, national posters, and shopping discounts.",
            prep_days=35,
            deadline_days=7
        ))

        return items

# Global singleton calendar provider
calendar_provider: BaseFestivalCalendarProvider = StaticRegistryCalendarProvider()
