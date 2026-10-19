# Chennai ward boundary dataset

## Source and attribution

This GeoJSON is derived from [Chennai/Wards.geojson in DataMeet's Municipal Spatial Data repository](https://github.com/datameet/Municipal_Spatial_Data/blob/master/Chennai/Wards.geojson).

The Chennai-specific [source README](https://github.com/datameet/Municipal_Spatial_Data/blob/master/Chennai/Readme.md) says the data was received from the [Transparent Chennai](http://www.transparentchennai.com/) team and identifies it as electoral wards for Chennai city. That Chennai-specific notice licenses the dataset under **Creative Commons Attribution-ShareAlike 2.5 India (CC BY-SA 2.5 India)**. This explicit Chennai-specific notice is the license used here.

- **Required attribution:** Chennai ward boundaries by the Transparent Chennai team, shared via DataMeet Municipal Spatial Data.
- **License:** [CC BY-SA 2.5 India](https://creativecommons.org/licenses/by-sa/2.5/in/).
- **Source file SHA:** `d9f04c3657e787ba61983e45454c089a2fa51a51` (source repository's `master` at the time this asset was imported).
- **Official reference:** [Greater Chennai Corporation ward maps and notifications](https://chennaicorporation.gov.in/gcc/delimited_ward/). The corporation advises users to refer to the Gazette notification where discrepancies arise.

## Local processing and validation

The source contained 201 features. The extra feature with `Ward_No: 0` was excluded because it is not one of the 200 numbered wards. The remaining features were validated for:

- exactly 200 polygons and one unique ward number for every integer from 1 through 200;
- Polygon geometries with closed rings;
- finite longitude/latitude coordinates within valid WGS 84 ranges.

The legacy `crs` member was removed so the file uses the RFC 7946 GeoJSON convention (WGS 84 longitude, latitude). Ward geometries and source properties are otherwise retained.

## Important limitation

This is a community-curated dataset, not an official Greater Chennai Corporation boundary export. It may not reflect every later administrative change. Verify against the latest GCC ward maps/Government Gazette before legal, official, emergency, or safety-critical use. The app uses these polygons for map navigation only; its weather values remain district-reference-point estimates and are **not ward-level measurements**.
