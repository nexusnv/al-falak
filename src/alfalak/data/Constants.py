from alfalak.data.Coordinates import Coordinates

# Kaaba location. Canonical value is 4 dp (21.4225N, 39.8262E, ~11 m);
# the stored 7-dp digits are display rounding kept for
# cross-port compatibility, not survey precision.
# NOTE: Coordinates is frozen — this shared singleton cannot be mutated
# (attribute assignment raises dataclasses.FrozenInstanceError).
MAKKAH: Coordinates = Coordinates(21.4225241, 39.8261818)

# IUGG mean Earth radius R1 = (2a + b) / 3, in kilometres.
# Pinned because 6371.0 / 6378.137 variants shift distances ~0.1-0.3%.
EARTH_MEAN_RADIUS_KM: float = 6371.0088
