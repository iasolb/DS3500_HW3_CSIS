import panel as pn
import folium
from folium import plugins
import pandas as pd
from api_file_AI import BostonDataAPI

# Initialize Panel
pn.extension('folium', sizing_mode='stretch_width')

class BostonDormDashboard:
    """Interactive dashboard for analyzing Northeastern dorms and nearby amenities"""
    
    def __init__(self):
        self.api = BostonDataAPI()
        self.api.load_data()
        
        # Initialize custom location
        self.custom_location = None
        
        # Color scheme for different categories
        self.colors = {
            'dorm': 'red',
            'grocery': 'green',
            'trader_joes': 'purple',
            'convenience_pharmacy': 'blue',
            'mbta': 'orange',
            'custom': 'darkred'
        }
        
        self.icons = {
            'dorm': 'home',
            'grocery': 'shopping-cart',
            'trader_joes': 'shopping-basket',
            'convenience_pharmacy': 'plus-square',
            'mbta': 'train',
            'custom': 'star'
        }
        
        # Create widgets
        self._create_widgets()
        
        # Create initial map
        self.map_pane = pn.pane.HTML(self._create_map(), sizing_mode='stretch_both')
    
    def _create_widgets(self):
        """Create all dashboard widgets"""
        # Filter checkboxes
        self.show_dorms = pn.widgets.Checkbox(name='Show Northeastern Dorms', value=True)
        self.show_grocery = pn.widgets.Checkbox(name='Show Grocery Stores', value=True)
        self.show_trader_joes = pn.widgets.Checkbox(name="Show Trader Joe's", value=True)
        self.show_convenience = pn.widgets.Checkbox(name='Show Convenience/Pharmacy', value=False)
        self.show_mbta = pn.widgets.Checkbox(name='Show MBTA Stops', value=True)
        
        # Custom location inputs
        self.custom_name = pn.widgets.TextInput(
            name='Location Name', 
            placeholder='e.g., My Apartment'
        )
        self.custom_lat = pn.widgets.FloatInput(
            name='Latitude', 
            value=42.3398,
            step=0.0001,
            start=42.0,
            end=43.0
        )
        self.custom_lng = pn.widgets.FloatInput(
            name='Longitude', 
            value=-71.0892,
            step=0.0001,
            start=-72.0,
            end=-70.0
        )
        self.add_custom_btn = pn.widgets.Button(
            name='Add Custom Location', 
            button_type='primary'
        )
        self.clear_custom_btn = pn.widgets.Button(
            name='Clear Custom Location', 
            button_type='warning'
        )
        
        # Analysis options
        self.selected_dorm = pn.widgets.Select(
            name='Analyze Specific Dorm',
            options=['All Dorms'] + [d['name'] for d in self.api.get_dorms_data()]
        )
        
        self.radius_filter = pn.widgets.FloatSlider(
            name='Search Radius (miles)',
            start=0.5,
            end=5.0,
            step=0.5,
            value=2.0
        )
        
        # Update button
        self.update_btn = pn.widgets.Button(
            name='Update Map', 
            button_type='success',
            width=200
        )
        
        # Bind callbacks
        self.update_btn.on_click(self._update_map)
        self.add_custom_btn.on_click(self._add_custom_location)
        self.clear_custom_btn.on_click(self._clear_custom_location)
    
    def _create_map(self):
        """Create the Folium map with all selected layers"""
        center_lat, center_lng = self.api.get_boston_center()
        
        # Create base map
        m = folium.Map(
            location=[center_lat, center_lng],
            zoom_start=13,
            tiles='OpenStreetMap'
        )
        
        # Add different layers based on selections
        if self.show_dorms.value:
            self._add_dorms_layer(m)
        
        if self.show_grocery.value:
            self._add_stores_layer(m, 'grocery')
        
        if self.show_trader_joes.value:
            self._add_stores_layer(m, 'trader_joes')
        
        if self.show_convenience.value:
            self._add_stores_layer(m, 'convenience_pharmacy')
        
        if self.show_mbta.value:
            self._add_mbta_layer(m)
        
        # Add custom location if exists
        if self.custom_location:
            self._add_custom_location_layer(m)
        
        # Add layer control
        folium.LayerControl().add_to(m)
        
        return m._repr_html_()
    
    def _add_dorms_layer(self, m):
        """Add Northeastern dorms to map"""
        dorms = self.api.get_dorms_data()
        dorms_group = folium.FeatureGroup(name='Northeastern Dorms')
        
        for dorm in dorms:
            # Create detailed popup
            popup_html = f"""
            <div style='width: 200px'>
                <h4>{dorm['name']}</h4>
                <b>Total Price:</b> ${dorm['price_total']:,.2f}<br>
                <b>Monthly (8 mo):</b> ${dorm['price_monthly']:,.2f}<br>
                <b>Location:</b> {dorm['lat']:.4f}, {dorm['lng']:.4f}
            </div>
            """
            
            folium.Marker(
                location=[dorm['lat'], dorm['lng']],
                popup=folium.Popup(popup_html, max_width=250),
                tooltip=dorm['name'],
                icon=folium.Icon(
                    color=self.colors['dorm'],
                    icon=self.icons['dorm'],
                    prefix='fa'
                )
            ).add_to(dorms_group)
        
        dorms_group.add_to(m)
    
    def _add_stores_layer(self, m, category):
        """Add store locations to map"""
        if category == 'grocery':
            stores = self.api.get_grocery_stores()
            layer_name = 'Grocery Stores'
        elif category == 'trader_joes':
            stores = self.api.get_trader_joes_in_boston()
            layer_name = "Trader Joe's"
        elif category == 'convenience_pharmacy':
            stores = self.api.get_convenience_pharmacy_stores()
            layer_name = 'Convenience & Pharmacy'
        else:
            return
        
        # Filter by radius if custom location exists
        if self.custom_location:
            stores = self.api.filter_by_radius(
                self.custom_location['lat'],
                self.custom_location['lng'],
                stores,
                self.radius_filter.value
            )
        
        stores_group = folium.FeatureGroup(name=layer_name)
        
        for store in stores[:50]:  # Limit to 50 stores for performance
            popup_html = f"""
            <div style='width: 200px'>
                <h4>{store['name']}</h4>
                <b>Address:</b> {store.get('address', 'N/A')}<br>
                <b>City:</b> {store.get('city', 'N/A')}
            </div>
            """
            
            folium.CircleMarker(
                location=[store['lat'], store['lng']],
                radius=6,
                popup=folium.Popup(popup_html, max_width=250),
                tooltip=store['name'],
                color=self.colors[category],
                fill=True,
                fillColor=self.colors[category],
                fillOpacity=0.7
            ).add_to(stores_group)
        
        stores_group.add_to(m)
    
    def _add_mbta_layer(self, m):
        """Add MBTA stops to map"""
        stops = self.api.get_mbta_stops()
        mbta_group = folium.FeatureGroup(name='MBTA Stops')
        
        # Color code by line
        line_colors = {
            'Red': 'red',
            'Orange': 'orange',
            'Blue': 'blue',
            'Green': 'green',
            'Silver': 'gray'
        }
        
        for stop in stops:
            line_color = line_colors.get(stop['line'], 'black')
            
            popup_html = f"""
            <div style='width: 200px'>
                <h4>{stop['name']}</h4>
                <b>Line:</b> {stop['line']}<br>
                <b>Route:</b> {stop.get('route', 'N/A')}
            </div>
            """
            
            folium.CircleMarker(
                location=[stop['lat'], stop['lng']],
                radius=8,
                popup=folium.Popup(popup_html, max_width=250),
                tooltip=f"{stop['name']} ({stop['line']} Line)",
                color=line_color,
                fill=True,
                fillColor=line_color,
                fillOpacity=0.8,
                weight=2
            ).add_to(mbta_group)
        
        mbta_group.add_to(m)
    
    def _add_custom_location_layer(self, m):
        """Add custom location and analysis"""
        if not self.custom_location:
            return
        
        custom_group = folium.FeatureGroup(name='Custom Location')
        
        # Add main marker
        folium.Marker(
            location=[self.custom_location['lat'], self.custom_location['lng']],
            popup=f"<b>{self.custom_location['name']}</b>",
            tooltip=self.custom_location['name'],
            icon=folium.Icon(
                color=self.colors['custom'],
                icon=self.icons['custom'],
                prefix='fa'
            )
        ).add_to(custom_group)
        
        # Add radius circle
        folium.Circle(
            location=[self.custom_location['lat'], self.custom_location['lng']],
            radius=self.radius_filter.value * 1609.34,  # Convert miles to meters
            color='darkred',
            fill=True,
            fillOpacity=0.1,
            weight=2,
            popup=f'Search radius: {self.radius_filter.value} miles'
        ).add_to(custom_group)
        
        # Analyze and show closest locations
        analysis = self.api.analyze_location(
            self.custom_location['name'],
            self.custom_location['lat'],
            self.custom_location['lng']
        )
        
        # Draw lines to closest grocery, trader joes, and mbta
        if analysis.get('closest_grocery') and len(analysis['closest_grocery']) > 0:
            closest = analysis['closest_grocery'][0]
            folium.PolyLine(
                locations=[
                    [self.custom_location['lat'], self.custom_location['lng']],
                    [closest['lat'], closest['lng']]
                ],
                color='green',
                weight=2,
                opacity=0.6,
                popup=f"Closest Grocery: {closest['name']} ({closest['distance']:.2f} mi)"
            ).add_to(custom_group)
        
        if analysis.get('closest_mbta') and len(analysis['closest_mbta']) > 0:
            closest = analysis['closest_mbta'][0]
            folium.PolyLine(
                locations=[
                    [self.custom_location['lat'], self.custom_location['lng']],
                    [closest['lat'], closest['lng']]
                ],
                color='orange',
                weight=2,
                opacity=0.6,
                popup=f"Closest T Stop: {closest['name']} ({closest['distance']:.2f} mi)"
            ).add_to(custom_group)
        
        custom_group.add_to(m)
    
    def _add_custom_location(self, event):
        """Add custom location to map"""
        if self.custom_name.value and self.custom_lat.value and self.custom_lng.value:
            self.custom_location = {
                'name': self.custom_name.value,
                'lat': self.custom_lat.value,
                'lng': self.custom_lng.value
            }
            self._update_map(event)
    
    def _clear_custom_location(self, event):
        """Clear custom location"""
        self.custom_location = None
        self.custom_name.value = ''
        self._update_map(event)
    
    def _update_map(self, event):
        """Update the map with current settings"""
        self.map_pane.object = self._create_map()
    
    def create_dashboard(self):
        """Create and return the complete dashboard layout"""
        
        # Title
        title = pn.pane.Markdown(
            "# 🏠 Northeastern Dorms Proximity Dashboard\n"
            "Analyze proximity to grocery stores, Trader Joe's, pharmacies, and MBTA stops",
            sizing_mode='stretch_width'
        )
        
        # Sidebar with controls
        sidebar = pn.Column(
            pn.pane.Markdown("## 🗺️ Map Layers"),
            self.show_dorms,
            self.show_grocery,
            self.show_trader_joes,
            self.show_convenience,
            self.show_mbta,
            pn.layout.Divider(),
            
            pn.pane.Markdown("## 📍 Add Custom Location"),
            self.custom_name,
            self.custom_lat,
            self.custom_lng,
            pn.Row(self.add_custom_btn, self.clear_custom_btn),
            pn.layout.Divider(),
            
            pn.pane.Markdown("## ⚙️ Settings"),
            self.radius_filter,
            self.update_btn,
            
            width=300,
            sizing_mode='stretch_height'
        )
        
        # Info panel
        info = pn.pane.Markdown(
            """
            ### 📊 How to Use:
            - **Toggle layers** to show/hide different amenities
            - **Add custom location** to compare with dorms
            - **Adjust search radius** to filter nearby stores
            - **Click markers** for detailed information
            - **Hover over markers** for quick tooltips
            
            ### 🎨 Color Legend:
            - 🔴 **Red**: Northeastern Dorms
            - 🟢 **Green**: Grocery Stores
            - 🟣 **Purple**: Trader Joe's
            - 🔵 **Blue**: Convenience/Pharmacy
            - 🟠 **Orange**: MBTA Stops
            - 🔴 **Dark Red**: Custom Location
            """,
            sizing_mode='stretch_width'
        )
        
        # Create statistics panel
        stats = self._create_stats_panel()
        
        # Layout
        dashboard = pn.template.FastListTemplate(
            title='Northeastern Dorms Analysis',
            sidebar=[sidebar],
            main=[
                title,
                info,
                stats,
                self.map_pane
            ],
            accent_base_color='#CC0000',
            header_background='#CC0000'
        )
        
        return dashboard
    
    def _create_stats_panel(self):
        """Create statistics panel"""
        dorms = self.api.get_dorms_data()
        
        stats_md = f"""
        ### 📈 Statistics
        - **Total Dorms**: {len(dorms)}
        - **Avg Monthly Price**: ${sum(d['price_monthly'] for d in dorms) / len(dorms):,.2f}
        - **Price Range**: ${min(d['price_monthly'] for d in dorms):,.2f} - ${max(d['price_monthly'] for d in dorms):,.2f}
        """
        
        if self.custom_location:
            analysis = self.api.analyze_location(
                self.custom_location['name'],
                self.custom_location['lat'],
                self.custom_location['lng']
            )
            
            closest_grocery = analysis.get('closest_grocery', [None])[0]
            closest_mbta = analysis.get('closest_mbta', [None])[0]
            
            if closest_grocery:
                stats_md += f"\n- **Closest Grocery**: {closest_grocery['name']} ({closest_grocery['distance']:.2f} mi)"
            if closest_mbta:
                stats_md += f"\n- **Closest T Stop**: {closest_mbta['name']} ({closest_mbta['distance']:.2f} mi)"
        
        return pn.pane.Markdown(stats_md, sizing_mode='stretch_width')


# Create and serve dashboard
if __name__ == '__main__':
    dashboard = BostonDormDashboard()
    app = dashboard.create_dashboard()
    app.show()
