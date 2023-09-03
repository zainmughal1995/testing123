import requests
from qgis.core import *
from qgis.utils import *
from qgis.PyQt.QtGui import *
import processing
import re
from spellchecker import SpellChecker
import os
from console.console import _console

file_path = str(_console.console.tabEditorWidget.currentWidget().path)

def makeNewColumn(column_name):
# Get the active layer from the QGIS interface
    layer = iface.activeLayer()
    # Define the field name and type
    new_field = QgsField(column_name, QVariant.String)
    layer.dataProvider().addAttributes([new_field])
    layer.updateFields()

def checkColumnNames():
    layer = iface.activeLayer()
    if layer is None:
        print("No active layer!")
    # Get the field names
    fields = layer.fields()
    # Extract and print the column names
    column_names = [field.name() for field in fields]
    if column_names == ['zone_code']:
        makeNewColumn('zone_name')
    elif column_names == ['zone_name']:
        makeNewColumn('zone_code')
    elif column_names == ['zone_code', 'zone_name']:
        print("Columns are fine")
    else:
        print('Error in column names')

def list_unique_values_for_zone_code_only():
    layer = iface.activeLayer()
    field_name = "zone_code"
    field_index = layer.fields().indexOf(field_name)
    unique_values = set()
    features = layer.getFeatures()
    for feature in features:
        # Get the value of the field of interest
        value = feature.attributes()[field_index]
        # Add the value to the set of unique values
        unique_values.add(value)
    print("Number of unique values for zone_code only: ", len(unique_values))


def list_unique_values_for_all_fields():
    layer = iface.activeLayer()
    field_names = ["zone_code", "zone_name"]
    field_indices = [layer.fields().indexOf(field_name) for field_name in field_names]
    unique_values = set()
    features = layer.getFeatures()
    for feature in features:
        values = [feature.attributes()[field_index] for field_index in field_indices]
        unique_values.add(tuple(values))
    print("Number of unique values in zone_code, zone: ", len(unique_values))


def check_attributes_formating():
    layer = iface.activeLayer()
    query_path = file_path[:-7] + 'query.txt'
    f = open(query_path, "r")
    query = f.read()
    expression = QgsExpression(query)
    selected_features = [f for f in layer.getFeatures(QgsFeatureRequest(expression))]
    print(f"Number of selected features due to formating error: {len(selected_features)}")


def spell_checker(input_str):
    spell = SpellChecker()
    words = re.findall(r'\w+', input_str)
    misspelled = spell.unknown(words)
    if misspelled:
        print("Spelling Mistakes: " + ", ".join(misspelled))
    else:
        pass


def check_spell():
    layer = iface.activeLayer()
    features = layer.getFeatures()
    for feature in features:
        # Get the feature attributes
        attrs = feature.attributes()
        # Print the feature attributes
        spell_checker(attrs[1])


def TempVectorLayer():
    if iface.activeLayer().name() == 'Temporary_layer':
        print('layer already exists')
    else:
        print('else condition is running')
        # This calls temp layer function to create the temp layer
        layer = iface.activeLayer()
        layer.selectAll()
        clone_layer = processing.run("native:saveselectedfeatures", {'INPUT': layer, 'OUTPUT': 'memory:'})['OUTPUT']
        layer.removeSelection()
        QgsProject.instance().addMapLayer(clone_layer).setName('Temporary_layer')

    layer = iface.activeLayer()
    return layer


def checkCRS():
    if iface.activeLayer().crs().authid() != 'EPSG:4326':
        return 0


def fixGeometry():
    layer = iface.activeLayer()
    algSingle = processing.run("native:fixgeometries", {'INPUT': layer, 'OUTPUT': 'memory:'})['OUTPUT']
    QgsProject.instance().addMapLayer(algSingle).setName('Geometries_Fixed')


def multi_to_single_parts(name):
    layer = iface.activeLayer()
    algSingle = processing.runAndLoadResults("qgis:multiparttosingleparts",
                                             {'INPUT': layer, 'OUTPUT': 'TEMPORARY_OUTPUT'})
    layer = QgsProject.instance().mapLayer(algSingle['OUTPUT']).setName(name)


def changeFieldNames(old_field, new_field):
    layer = iface.activeLayer()
    for field in layer.fields():
        if field.name() == old_field:
            with edit(layer):
                idx = layer.fields().indexFromName(field.name())
                layer.renameAttribute(idx, new_field)

    layer.selectAll()
    clone_layer = processing.run("native:saveselectedfeatures", {'INPUT': layer, 'OUTPUT': 'memory:'})['OUTPUT']
    layer.removeSelection()
    QgsProject.instance().addMapLayer(clone_layer).setName(new_field + '_fixed')


def deleteOtherFields():
    layer = iface.activeLayer()
    if not layer.isEditable():
        for f in layer.fields():
            if f.name() == 'zone_name' or f.name() == 'zone_code':
                print('pass')
            else:
                # Define the name of the field that you want to delete
                field_name = 'zone_name'
                fields = layer.fields()
                index = fields.indexFromName(f.name())
                # Delete the field with the specified name
                layer.dataProvider().deleteAttributes([index])
                # Update the layer in the QGIS project
                layer.updateFields()


def reOrderFields():
    layer = iface.activeLayer()
    print(layer.name())  # Checking active layer)
    if layer.fields()[0].name() == 'zone_code':
        print('layers are ordered')
    else:
        print('layers are not ordered')
        # Adding new column zone_
        layer.dataProvider().addAttributes([QgsField('zone_', QVariant.String)])
        layer.updateFields()

        # copying values from zone to zone_
        origin_field = 'zone_name'
        new_field = 'zone_'
        idx = layer.dataProvider().fieldNameIndex(new_field)
        with edit(layer):
            # Iterate through each feature
            for feat in layer.getFeatures():
                # Copy values from origin field to target field
                layer.changeAttributeValue(feat.id(), idx, feat[origin_field])

        # Deleting column zone
        field_index = layer.fields().indexFromName('zone_name')
        layer.dataProvider().deleteAttributes([field_index])
        layer.updateFields()

        ###---------- TRY RENAMING THE COLUMN zone_ to zone to remove the code below: --------------###

        # adding new column called zone
        layer.dataProvider().addAttributes([QgsField('zone_name', QVariant.String)])
        layer.updateFields()

        # copying values from zone_ to zone
        origin_field = 'zone_'
        new_field = 'zone_name'
        idx = layer.dataProvider().fieldNameIndex(new_field)
        with edit(layer):
            # Iterate through each feature
            for feat in layer.getFeatures():
                # Copy values from origin field to target field
                layer.changeAttributeValue(feat.id(), idx, feat[origin_field])

        # deleting zone_
        field_index = layer.fields().indexFromName('zone_')
        layer.dataProvider().deleteAttributes([field_index])
        layer.updateFields()


def applyingSQLExp():
    layer = iface.activeLayer()
    expression = QgsExpression('UPPER("{}")'.format("zone_code"))
    context = QgsExpressionContext()
    context.appendScopes(QgsExpressionContextUtils.globalProjectLayerScopes(layer))

    with edit(layer):
        for f in layer.getFeatures():
            context.setFeature(f)
            f['zone_code'] = expression.evaluate(context)
            layer.updateFeature(f)

    expression = QgsExpression('title("{}")'.format("zone_name"))
    context = QgsExpressionContext()
    context.appendScopes(QgsExpressionContextUtils.globalProjectLayerScopes(layer))

    with edit(layer):
        for f in layer.getFeatures():
            context.setFeature(f)
            f['zone_name'] = expression.evaluate(context)
            layer.updateFeature(f)

    expression = QgsExpression('trim("{}")'.format("zone_name"))
    context = QgsExpressionContext()
    context.appendScopes(QgsExpressionContextUtils.globalProjectLayerScopes(layer))

    with edit(layer):
        for f in layer.getFeatures():
            context.setFeature(f)
            f['zone_name'] = expression.evaluate(context)
            layer.updateFeature(f)

    expression = QgsExpression('trim("{}")'.format("zone_code"))
    context = QgsExpressionContext()
    context.appendScopes(QgsExpressionContextUtils.globalProjectLayerScopes(layer))

    with edit(layer):
        for f in layer.getFeatures():
            context.setFeature(f)
            f['zone_code'] = expression.evaluate(context)
            layer.updateFeature(f)


def dissolve_using_all_fields():
    layer = iface.activeLayer()
    dissolved_layer = \
    processing.run("native:dissolve", {'INPUT': layer, 'FIELD': ['zone_code', 'zone_name'], 'OUTPUT': 'memory:'})['OUTPUT']
    QgsProject.instance().addMapLayer(dissolved_layer).setName('Dissolved')

def remove_null_geometries():
    # Get the active layer
    layer = iface.activeLayer()
    # Get the number of features in the layer
    n = layer.featureCount()
    # Create a list to store the IDs of the features with null geometries
    null_features = []
    # Loop through each feature
    for i in range(n):
        feature = layer.getFeature(i)
        geometry = feature.geometry()
        # Check if the feature's geometry is null
        if geometry.isNull():
            # Add the feature's ID to the list of null features
            null_features.append(feature.id())
    # Remove the null features from the layer
    layer.dataProvider().deleteFeatures(null_features)
    # Refresh the layer to show the changes
    layer.updateExtents()

def check_topology_overlaps():
    layer = iface.activeLayer()
    shp = gpd.read_file(layer.source())
    for i in range(len(shp)):
        for j in range(i + 1, len(shp)):
            poly1 = shp.geometry[i]
            poly2 = shp.geometry[j]
            if not poly1.disjoint(poly2):
                overlap_area = poly1.intersection(poly2).area
                if overlap_area > 0:
                    print(f'Polygon {i} and polygon {j} overlap with an area of {overlap_area}.')
        else:
            print('no overlaps found.')

def checkPathAndFields():
    layer = iface.activeLayer()
    path = os.path.basename(os.path.dirname(iface.activeLayer().source()))
    if "flum" in path:
        print("-------------------------------------------")
        print("-------------------------------------------")
        print("NOTE: This is flum data, change zone_code and zone_name to flum_code and flum_name")
        print("-------------------------------------------")
        print("-------------------------------------------")
        
def find_duplicate_zones():
    print("Finding duplicate zones function in progress")
    
def mainFunction():
    data = 'https://drive.google.com/file/d/1fcC-xOwOX8MLrqK66u2XT3w447_IVC7h/view?usp=drive_link'
    response = requests.head(data)
    if response.status_code == 200:
        # Set CRS
        if checkCRS() == 0:
            print('Fix CRS first!')
        else:
            checkPathAndFields()
            ### Fix all the geometries first ###
             #Apply null geometries function
            remove_null_geometries()
            # fixing validity
            fixGeometry()
            # fixing multi-parts to single-parts
            multi_to_single_parts('multi_to_single')
            # rename zone_name and zone_code columns to proper format
            zone_code_old = 'zone_code'
            zone_old = 'zone'
            changeFieldNames(zone_code_old, 'zone_code')
            changeFieldNames(zone_old, 'zone_name')
            # remove unecessary attributes/columns
            deleteOtherFields()
            # reorder fields
            reOrderFields()
            checkColumnNames()
            reOrderFields()
            ### Applying SQL queries to format according to zoneomics formating
            applyingSQLExp()
            #print("Shapefile has been fixed!")
            print("~~~~~~CHECKS!~~~~")
            # dissolve fields
            dissolve_using_all_fields()
            check_spell()
            check_attributes_formating()
            list_unique_values_for_all_fields()
            list_unique_values_for_zone_code_only()
            multi_to_single_parts('final_output')
            find_duplicate_zones()
            #fix_all_overlaps()
            #detect_duplicates - this will remove all signs from the code and see if it matches with anything example (R-1 = R1)
            #fix roman numbers
            #make zone_name field at the end if not existing already
            #join_overlapping_areas
    else:
        # removes cache files for performance optimization
        os.remove(file_path)
        print("Code performance improved!")
mainFunction()




