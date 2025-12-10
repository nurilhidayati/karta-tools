"""
Custom Draw plugin for Folium that supports drawing and editing features.
Based on Leaflet.draw plugin.
"""
from folium import Map, Icon, Marker, GeoJson
from folium.plugins import Draw
import json


class NewDraw(Draw):
    """
    Extended Draw plugin with additional features for better drawing experience.
    
    Inherits from folium.plugins.Draw and adds custom configurations.
    """
    
    def __init__(self, export=False, filename='data.geojson', position='topleft',
                 draw_options=None, edit_options=None):
        """
        Initialize the NewDraw plugin.
        
        Parameters
        ----------
        export : bool, default False
            Add a button to export drawn features to a GeoJSON file
        filename : str, default 'data.geojson'
            Name of the file to export
        position : str, default 'topleft'
            Position of the draw controls on the map
        draw_options : dict, optional
            Options for drawing controls
        edit_options : dict, optional
            Options for editing controls
        """
        
        # Default draw options
        if draw_options is None:
            draw_options = {
                'polyline': {
                    'allowIntersection': True,
                    'showLength': True,
                    'metric': True,
                    'feet': False,
                    'nautic': False,
                    'shapeOptions': {
                        'color': '#3388ff',
                        'weight': 4,
                        'opacity': 0.8
                    }
                },
                'polygon': {
                    'allowIntersection': False,
                    'showArea': True,
                    'drawError': {
                        'color': '#e1e100',
                        'message': '<strong>Error:</strong> Shape edges cannot cross!'
                    },
                    'shapeOptions': {
                        'color': '#3388ff',
                        'fillOpacity': 0.3
                    }
                },
                'circle': {
                    'shapeOptions': {
                        'color': '#3388ff',
                        'fillOpacity': 0.3
                    }
                },
                'rectangle': {
                    'showArea': True,
                    'shapeOptions': {
                        'color': '#3388ff',
                        'fillOpacity': 0.3
                    }
                },
                'marker': True,
                'circlemarker': {
                    'color': '#3388ff',
                    'fillOpacity': 0.8
                }
            }
        
        # Default edit options
        if edit_options is None:
            edit_options = {
                'edit': True,
                'remove': True
            }
        
        # Initialize parent Draw class
        super().__init__(
            export=export,
            filename=filename,
            position=position,
            draw_options=draw_options,
            edit_options=edit_options
        )


