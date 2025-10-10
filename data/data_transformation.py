import geopandas as gpd
import os

# Define base directory (assuming script is in data/ folder)
base_dir = os.path.dirname(os.path.abspath(__file__))
output_dir = '/Users/cassiecinzori/Documents/fall2025/DataScience/DS3500_HW3_CSIS'

# Define shapefile paths relative to the script location
shapefiles = {
    'mbta_nodes': os.path.join(base_dir, 'MBTA_data/MBTA Rapid Transit Labels/GISDATA_MBTA_NODEPoint.shp'),
    'mbta_lines': os.path.join(base_dir, 'MBTA_data/MBTA Rapid Transit Lines/GISDATA_MBTA_ARCLine.shp'),
    'northeastern_dorms': os.path.join(base_dir, 'NortheasternDorm_data/layers/POINT.shp')
}

# Convert each shapefile to CSV
for name, shapefile_path in shapefiles.items():
    print(f"Processing {name}...")

    # Read shapefile
    gdf = gpd.read_file(shapefile_path)

    # Convert geometry to WKT string
    gdf['geometry'] = gdf['geometry'].apply(lambda geom: geom.wkt)

    # Define output path
    output_file = os.path.join(output_dir, f'{name}.csv')

    # Save to CSV
    gdf.to_csv(output_file, index=False)

    print(f"  Saved to: {output_file}")

print("\nAll shapefiles converted successfully!")