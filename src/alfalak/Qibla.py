import math
import numbers
from decimal import Decimal

from alfalak.astronomy.Geodesy import geodesic_inverse
from alfalak.data.Constants import EARTH_MEAN_RADIUS_KM, MAKKAH
from alfalak.data.Coordinates import Coordinates
from alfalak.exceptions import ConfigurationError, ValidationError
from alfalak.util.FloatUtil import unwind_angle

__all__ = ["MAKKAH", "Qibla"]

_SPHERICAL = "spherical"
_ELLIPSOIDAL = "ellipsoidal"


class Qibla:
    """
    Qibla direction and distance for a location.

    ``direction`` is degrees clockwise from north; ``distance_to_makkah_km``
    is the distance in kilometres. Both follow the selected Earth model.

    ``method="spherical"`` (default) uses spherical trigonometry (Todhunter
    "Spherical Trigonometry" p.50, ported from upstream adhan) with the IUGG
    mean radius for distance. ``method="ellipsoidal"`` uses the Karney
    geodesic inverse on the WGS84 ellipsoid (see ``alfalak.astronomy.Geodesy``).

    Spherical-Earth assumption: typically within a few arcminutes of the
    WGS84 ellipsoidal forward azimuth, worst case ~0.3-0.35 deg (NOT
    sub-0.1 deg; per published spherical-vs-ellipsoidal comparisons:
    IJRS great-circle study up to ~20 arcmin, Walisongo/Al-Hilal ~8 arcmin
    vs Vincenty).

    Degenerate inputs do not raise: Makkah-to-self and the true antipode
    (~-21.4225, -140.17, where every bearing is equidistant) return a float
    in [0, 360). At the exact self point both models return 180.0 by
    construction (spherical atan2(0, ~0) and the ellipsoidal meridian
    path); any bearing is equally valid there.

    ``method="ellipsoidal"`` may raise :class:`AstronomicalError` if the
    Karney iteration fails to converge (defensive; it converges for all
    inputs on WGS84). ``method`` must be exactly ``"spherical"`` (default)
    or ``"ellipsoidal"`` (case-sensitive); anything else raises
    :class:`ConfigurationError`.
    """

    def __init__(
        self,
        coordinates: tuple[float, float] | Coordinates,
        method: str = _SPHERICAL,
    ) -> None:
        if method not in (_SPHERICAL, _ELLIPSOIDAL):
            raise ConfigurationError(
                "Qibla method must be 'spherical' or 'ellipsoidal', " f"got {method!r}."
            )
        self.method: str = method
        if isinstance(coordinates, Coordinates):
            latitude = coordinates.latitude
            longitude = coordinates.longitude
        else:
            try:
                latitude, longitude = coordinates
            except (TypeError, ValueError) as e:
                raise ValidationError(
                    "Coordinates must be a (latitude, longitude) tuple or "
                    f"Coordinates, got {coordinates!r}."
                ) from e
            # Reuse Coordinates validation so non-numeric inputs raise
            # ValidationError (not bare TypeError), per the AlFalakError contract.
            validated = Coordinates(latitude, longitude)
            latitude, longitude = validated.latitude, validated.longitude

        if method == _ELLIPSOIDAL:
            azimuth_deg, distance_m = geodesic_inverse(
                latitude, longitude, MAKKAH.latitude, MAKKAH.longitude
            )
            direction = unwind_angle(azimuth_deg)
            distance_km = distance_m / 1000.0
        else:
            # Equation from "Spherical Trigonometry For the use of colleges
            # and schools" page 50
            longitude_delta = math.radians(MAKKAH.longitude - longitude)
            latitude_radians = math.radians(latitude)
            term1 = math.sin(longitude_delta)
            term2 = math.cos(latitude_radians) * math.tan(math.radians(MAKKAH.latitude))
            term3 = math.sin(latitude_radians) * math.cos(longitude_delta)
            direction = unwind_angle(math.degrees(math.atan2(term1, term2 - term3)))

            # Spherical great-circle distance via the haversine atan2 form
            # (stable near 0 and antipode; naive law-of-cosines is not).
            phi1 = math.radians(latitude)
            phi2 = math.radians(MAKKAH.latitude)
            delta_phi = phi2 - phi1
            delta_lambda = math.radians(MAKKAH.longitude - longitude)
            haversine_a = (
                math.sin(delta_phi / 2) ** 2
                + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
            )
            haversine_a = min(1.0, max(0.0, haversine_a))
            central_angle = 2 * math.atan2(
                math.sqrt(haversine_a), math.sqrt(1 - haversine_a)
            )
            distance_km = EARTH_MEAN_RADIUS_KM * central_angle

        self.direction: float = direction
        self.distance_to_makkah_km: float = distance_km

    def magnetic_direction(self, declination_deg: numbers.Real | Decimal) -> float:
        """Compass heading toward Makkah for a magnetic compass.

        ``direction`` is always true-north (that is the default); pass your
        local magnetic declination to get the needle heading instead:

        ``magnetic = unwind(true - declination_east)`` ("east is least").

        Sign convention (NOAA NCEI): declination is positive east of true
        north, negative west. So 10 deg E subtracts 10 deg, while 8 deg W
        (pass -8) adds 8 deg. Any finite value is accepted; the result is
        unwound to [0, 360).

        The declination itself is NOT computed here — look it up from a
        phone compass, chart, or magnetic model. A future model-backed
        provider will live behind this hook and must take (model, epoch):
        the field drifts (secular variation; e.g. WMM2025, valid 2025–2030
        on a 5-year cycle), so a timeless cached declination goes stale.
        """
        if isinstance(declination_deg, bool) or not isinstance(
            declination_deg, (numbers.Real, Decimal)
        ):
            raise ValidationError(
                "Declination must be a real number of degrees east, "
                f"got {declination_deg!r}."
            )
        try:
            declination = float(declination_deg)
        except (OverflowError, ValueError) as e:
            raise ValidationError(
                "Declination must be finite, " f"got {declination_deg!r}."
            ) from e
        if not math.isfinite(declination):
            raise ValidationError(
                "Declination must be finite, " f"got {declination_deg!r}."
            )
        # Reduce modulo 360 first: unwind_angle's floor-based remainder loses
        # all precision for huge finite inputs (catastrophic cancellation),
        # while math.fmod is exactly rounded. Identity for |d| < 360.
        return unwind_angle(self.direction - math.fmod(declination, 360.0))
