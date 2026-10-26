"""Places (taluk headquarters and major towns) inside each Tamil Nadu district.

Each place is a *point* (approximate town-centre coordinates, rounded to ~0.01 degrees),
not an administrative boundary. Weather for a place is a model/grid estimate at that
point, exactly like the district-level values; it is not a station observation.

The coordinates were compiled by hand and are only meant to be accurate enough for a
~10 km weather grid. ``tests/test_app.py`` guards against gross mistakes (every place
must be inside Tamil Nadu and near its district's reference point), but they have not been
verified against an official gazetteer. Add or correct entries here; no other file needs to
change.
"""
import re

from .districts import DISTRICTS

# district id -> [(place name, latitude, longitude), ...]
_RAW_PLACES = {
    "ariyalur": [("Ariyalur", 11.14, 79.08), ("Jayankondam", 11.21, 79.36), ("Udayarpalayam", 11.20, 79.29), ("Sendurai", 11.27, 79.14)],
    "chengalpattu": [("Chengalpattu", 12.68, 79.99), ("Tambaram", 12.92, 80.10), ("Madurantakam", 12.50, 79.89), ("Tirukalukundram", 12.61, 80.06), ("Mamallapuram", 12.63, 80.19), ("Cheyyur", 12.35, 79.99), ("Thiruporur", 12.72, 80.19)],
    "chennai": [("Egmore", 13.07, 80.26), ("Mylapore", 13.04, 80.27), ("Guindy", 13.01, 80.22), ("Adyar", 13.00, 80.26), ("Perambur", 13.11, 80.24), ("Tondiarpet", 13.13, 80.29), ("Anna Nagar", 13.09, 80.21), ("Ambattur", 13.11, 80.15), ("Sholinganallur", 12.90, 80.23)],
    "coimbatore": [("Coimbatore", 11.02, 76.96), ("Pollachi", 10.66, 77.00), ("Mettupalayam", 11.30, 76.94), ("Sulur", 11.03, 77.13), ("Valparai", 10.33, 76.95), ("Annur", 11.24, 77.11), ("Madukkarai", 10.91, 76.96), ("Kinathukadavu", 10.82, 77.02)],
    "cuddalore": [("Cuddalore", 11.75, 79.77), ("Chidambaram", 11.40, 79.69), ("Kurinjipadi", 11.56, 79.59), ("Panruti", 11.77, 79.55), ("Virudhachalam", 11.52, 79.33), ("Neyveli", 11.54, 79.49), ("Bhuvanagiri", 11.44, 79.65), ("Kattumannarkoil", 11.29, 79.55)],
    "dharmapuri": [("Dharmapuri", 12.12, 78.16), ("Harur", 12.05, 78.48), ("Palacode", 12.31, 78.07), ("Pennagaram", 12.13, 77.90), ("Pappireddipatti", 11.96, 78.36)],
    "dindigul": [("Dindigul", 10.37, 77.98), ("Palani", 10.45, 77.52), ("Kodaikanal", 10.24, 77.49), ("Oddanchatram", 10.48, 77.75), ("Natham", 10.22, 78.23), ("Vedasandur", 10.53, 77.95), ("Nilakottai", 10.17, 77.85), ("Batlagundu", 10.16, 77.76)],
    "erode": [("Erode", 11.34, 77.72), ("Gobichettipalayam", 11.45, 77.44), ("Bhavani", 11.45, 77.68), ("Perundurai", 11.28, 77.58), ("Sathyamangalam", 11.50, 77.24), ("Anthiyur", 11.58, 77.59), ("Kodumudi", 11.08, 77.89)],
    "kallakurichi": [("Kallakurichi", 11.74, 78.96), ("Sankarapuram", 11.89, 78.88), ("Ulundurpet", 11.69, 79.29), ("Tirukoilur", 11.97, 79.20)],
    "kanchipuram": [("Kancheepuram", 12.82, 79.69), ("Sriperumbudur", 12.97, 79.94), ("Walajabad", 12.79, 79.83), ("Uthiramerur", 12.61, 79.76), ("Kundrathur", 12.99, 80.10)],
    "kanniyakumari": [("Nagercoil", 8.18, 77.41), ("Kanniyakumari", 8.09, 77.54), ("Thuckalay", 8.25, 77.30), ("Marthandam", 8.31, 77.23), ("Colachel", 8.18, 77.25)],
    "karur": [("Karur", 10.96, 78.08), ("Kulithalai", 10.93, 78.42), ("Aravakurichi", 10.77, 77.90), ("Krishnarayapuram", 10.96, 78.27)],
    "krishnagiri": [("Krishnagiri", 12.52, 78.21), ("Hosur", 12.74, 77.83), ("Denkanikottai", 12.53, 77.79), ("Pochampalli", 12.35, 78.37), ("Uthangarai", 12.27, 78.53), ("Shoolagiri", 12.66, 78.02)],
    "madurai": [("Madurai", 9.93, 78.12), ("Melur", 10.03, 78.34), ("Usilampatti", 9.97, 77.79), ("Thirumangalam", 9.82, 77.99), ("Vadipatti", 10.08, 77.95), ("Peraiyur", 9.74, 77.79)],
    "mayiladuthurai": [("Mayiladuthurai", 11.10, 79.65), ("Sirkazhi", 11.24, 79.74), ("Kuthalam", 11.01, 79.54), ("Tharangambadi", 11.03, 79.85), ("Poompuhar", 11.15, 79.85)],
    "nagapattinam": [("Nagapattinam", 10.77, 79.84), ("Vedaranyam", 10.37, 79.85), ("Velankanni", 10.68, 79.85), ("Kilvelur", 10.73, 79.76)],
    "namakkal": [("Namakkal", 11.22, 78.17), ("Rasipuram", 11.46, 78.17), ("Tiruchengode", 11.38, 77.89), ("Paramathi Velur", 11.12, 78.01), ("Kumarapalayam", 11.44, 77.70), ("Kolli Hills", 11.25, 78.34)],
    "nilgiris": [("Udhagamandalam (Ooty)", 11.41, 76.70), ("Coonoor", 11.35, 76.80), ("Kotagiri", 11.42, 76.86), ("Gudalur", 11.50, 76.49), ("Wellington", 11.37, 76.78)],
    "perambalur": [("Perambalur", 11.23, 78.88), ("Veppanthattai", 11.38, 78.94)],
    "pudukkottai": [("Pudukkottai", 10.38, 78.82), ("Aranthangi", 10.17, 78.99), ("Alangudi", 10.36, 78.97), ("Karambakudi", 10.46, 79.13), ("Thirumayam", 10.25, 78.75), ("Gandarvakottai", 10.57, 78.95), ("Illuppur", 10.52, 78.62)],
    "ramanathapuram": [("Ramanathapuram", 9.36, 78.84), ("Rameswaram", 9.29, 79.31), ("Paramakudi", 9.55, 78.59), ("Mudukulathur", 9.34, 78.51), ("Kilakarai", 9.23, 78.79), ("Kamuthi", 9.41, 78.37)],
    "ranipet": [("Ranipet", 12.92, 79.33), ("Arakkonam", 13.08, 79.67), ("Arcot", 12.91, 79.32), ("Walajapet", 12.92, 79.37), ("Sholinghur", 13.12, 79.42)],
    "salem": [("Salem", 11.66, 78.15), ("Attur", 11.60, 78.60), ("Mettur", 11.79, 77.80), ("Omalur", 11.74, 78.04), ("Edappadi", 11.58, 77.83), ("Yercaud", 11.78, 78.21), ("Sankari", 11.48, 77.94)],
    "sivaganga": [("Sivaganga", 9.84, 78.48), ("Karaikudi", 10.07, 78.78), ("Devakottai", 9.95, 78.82), ("Manamadurai", 9.69, 78.46), ("Tiruppattur (Sivaganga)", 10.12, 78.50)],
    "tenkasi": [("Tenkasi", 8.96, 77.32), ("Kadayanallur", 9.07, 77.34), ("Sankarankovil", 9.17, 77.54), ("Shencottah", 8.96, 77.25), ("Alangulam", 8.87, 77.49), ("Courtallam", 8.93, 77.27), ("Puliyangudi", 9.17, 77.40), ("Sivagiri", 9.34, 77.43)],
    "thanjavur": [("Thanjavur", 10.79, 79.14), ("Kumbakonam", 10.96, 79.38), ("Pattukkottai", 10.43, 79.32), ("Peravurani", 10.29, 79.19), ("Orathanadu", 10.63, 79.28), ("Papanasam", 10.92, 79.27), ("Thiruvaiyaru", 10.88, 79.10)],
    "theni": [("Theni", 10.01, 77.48), ("Periyakulam", 10.12, 77.55), ("Bodinayakanur", 10.01, 77.35), ("Uthamapalayam", 9.81, 77.33), ("Andipatti", 10.00, 77.62), ("Cumbum", 9.74, 77.28)],
    "thoothukudi": [("Thoothukudi", 8.76, 78.13), ("Kovilpatti", 9.17, 77.87), ("Tiruchendur", 8.49, 78.12), ("Srivaikuntam", 8.63, 77.91), ("Sattankulam", 8.44, 77.91), ("Ettayapuram", 9.15, 77.99), ("Vilathikulam", 9.13, 78.16), ("Ottapidaram", 8.94, 78.02)],
    "tiruchirappalli": [("Tiruchirappalli", 10.79, 78.70), ("Srirangam", 10.86, 78.69), ("Lalgudi", 10.87, 78.82), ("Musiri", 10.95, 78.44), ("Manapparai", 10.61, 78.42), ("Thuraiyur", 11.15, 78.59)],
    "tirunelveli": [("Tirunelveli", 8.71, 77.76), ("Palayamkottai", 8.72, 77.74), ("Ambasamudram", 8.71, 77.45), ("Nanguneri", 8.49, 77.66), ("Cheranmahadevi", 8.69, 77.56), ("Valliyur", 8.38, 77.62)],
    "tirupathur": [("Tirupathur", 12.50, 78.57), ("Vaniyambadi", 12.68, 78.62), ("Ambur", 12.79, 78.72), ("Jolarpettai", 12.57, 78.58)],
    "tiruppur": [("Tiruppur", 11.11, 77.34), ("Palladam", 10.99, 77.28), ("Avinashi", 11.19, 77.27), ("Dharapuram", 10.74, 77.52), ("Udumalaipettai", 10.59, 77.25), ("Kangeyam", 11.00, 77.56)],
    "tiruvallur": [("Tiruvallur", 13.14, 79.91), ("Poonamallee", 13.05, 80.10), ("Ponneri", 13.34, 80.20), ("Tiruttani", 13.18, 79.62), ("Gummidipoondi", 13.41, 80.11), ("Avadi", 13.12, 80.10), ("Uthukottai", 13.33, 79.89)],
    "tiruvannamalai": [("Tiruvannamalai", 12.23, 79.07), ("Arani", 12.67, 79.28), ("Polur", 12.51, 79.13), ("Cheyyar", 12.66, 79.54), ("Vandavasi", 12.50, 79.62), ("Chengam", 12.31, 78.79)],
    "tiruvarur": [("Tiruvarur", 10.77, 79.64), ("Mannargudi", 10.67, 79.45), ("Thiruthuraipoondi", 10.53, 79.64), ("Nannilam", 10.87, 79.62), ("Kudavasal", 10.84, 79.50), ("Muthupet", 10.39, 79.51), ("Needamangalam", 10.77, 79.42)],
    "vellore": [("Vellore", 12.92, 79.13), ("Katpadi", 12.97, 79.14), ("Gudiyatham", 12.95, 78.87), ("Pernambut", 12.94, 78.72)],
    "viluppuram": [("Viluppuram", 11.94, 79.49), ("Tindivanam", 12.24, 79.65), ("Gingee", 12.25, 79.42), ("Marakkanam", 12.19, 79.94), ("Vikravandi", 11.99, 79.53)],
    "virudhunagar": [("Virudhunagar", 9.57, 77.96), ("Sivakasi", 9.45, 77.80), ("Srivilliputhur", 9.51, 77.63), ("Rajapalayam", 9.45, 77.55), ("Aruppukkottai", 9.51, 78.10), ("Sattur", 9.36, 77.91)],
}


def _slug(name):
    return re.sub(r"[^a-z0-9]+", "-", name.casefold()).strip("-")


def _build():
    by_district = {}
    for district in DISTRICTS:
        by_district[district["id"]] = [
            {"id": _slug(name), "name": name, "district_id": district["id"], "lat": lat, "lon": lon}
            for name, lat, lon in _RAW_PLACES.get(district["id"], [])
        ]
    return by_district


PLACES_BY_DISTRICT = _build()


def places_for_district(district_id):
    """Return the places of a district, or ``None`` if the district id is unknown."""
    return PLACES_BY_DISTRICT.get(str(district_id).strip().casefold())


def place_by_id(district_id, place_id):
    for place in places_for_district(district_id) or []:
        if place["id"] == str(place_id).strip().casefold():
            return place
    return None
