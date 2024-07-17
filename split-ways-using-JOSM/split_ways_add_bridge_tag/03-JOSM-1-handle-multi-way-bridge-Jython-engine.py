from org.openstreetmap.josm.gui import MainApplication
from org.openstreetmap.josm.data.coor import LatLon
from org.openstreetmap.josm.data.osm import Node, Way, OsmPrimitiveType
from org.openstreetmap.josm.actions import SplitWayAction
from org.openstreetmap.josm.command import AddCommand, ChangeCommand
from org.openstreetmap.josm.tools import Geometry
from org.openstreetmap.josm.data.projection import ProjectionRegistry
from org.openstreetmap.josm.data import UndoRedoHandler
from org.openstreetmap.josm.command import ChangePropertyCommand
import java.util.ArrayList

# Constants
BRIDGE_TAG = "bridge"
BRIDGE_VALUE = "yes"
BRIDGE_ID_TAG = "bridge:id"

coordinatesList = [
    {
        "points": [
            {"latitude": 36.6490109994807, "longitude": -89.06306871832646, "wayId": 16208279},
            {"latitude": 36.649008842327014, "longitude": -89.06324527869246, "wayId": 16208919},
        ],
        "additionalBridgeWayIds": [],
        "bridgeId": "098C00033N"
    }
]

def tagWayAsBridge(way, bridgeId):
    addTagCommand = ChangePropertyCommand(way, BRIDGE_TAG, BRIDGE_VALUE)
    UndoRedoHandler.getInstance().add(addTagCommand)
    addBridgeIdCommand = ChangePropertyCommand(way, BRIDGE_ID_TAG, bridgeId)
    UndoRedoHandler.getInstance().add(addBridgeIdCommand)
    print("Way %d tagged successfully." % way.getId())

def getDataSet():
    return MainApplication.getLayerManager().getEditDataSet()

def addNodeToWay(way, latLon, isFirstPoint, preExistingNode, bridgeId):
    dataSet = getDataSet()
    projection = ProjectionRegistry.getProjection()
    wayNodes = way.getNodes()
    closestIndex = -1
    closestDistance = float('inf')
    closestLatLon = latLon

    for i in range(len(wayNodes) - 1):
        segmentStart = projection.latlon2eastNorth(wayNodes[i].getCoor())
        segmentEnd = projection.latlon2eastNorth(wayNodes[i + 1].getCoor())
        point = Geometry.closestPointToSegment(
            segmentStart,
            segmentEnd,
            projection.latlon2eastNorth(latLon)
        )
        pointLatLon = projection.eastNorth2latlon(point)
        distance = latLon.greatCircleDistance(pointLatLon)
        if distance < closestDistance:
            closestDistance = distance
            closestIndex = i
            closestLatLon = pointLatLon

    if closestIndex != -1:
        closestNode = Node(closestLatLon)
        newWayNodes = java.util.ArrayList(wayNodes)
        newWayNodes.add(closestIndex + 1, closestNode)

        newWay = Way(way)
        newWay.setNodes(newWayNodes)

        UndoRedoHandler.getInstance().add(AddCommand(dataSet, closestNode))
        UndoRedoHandler.getInstance().add(ChangeCommand(way, newWay))

        dataSet.setSelected(closestNode)
        SplitWayAction.runOn(dataSet)

        print("Node added at latitude: %f, longitude: %f and Node ID: %d" % (latLon.lat(), latLon.lon(), closestNode.getId()))

        # Tag the appropriate way as a bridge
        selectedWays = dataSet.getSelectedWays()
        for selectedWay in selectedWays:
            selectedWayNodes = selectedWay.getNodes()
            isBridgeWay = False

            if isFirstPoint:
                isBridgeWay = (selectedWayNodes[0] == closestNode and selectedWayNodes[-1] == preExistingNode) or (selectedWayNodes[-1] == closestNode and selectedWayNodes[0] == preExistingNode)
            else:
                isBridgeWay = (selectedWayNodes[0] == preExistingNode and selectedWayNodes[-1] == closestNode) or (selectedWayNodes[-1] == preExistingNode and selectedWayNodes[0] == closestNode)

            if isBridgeWay:
                tagWayAsBridge(selectedWay, bridgeId)
                break

        return closestNode
    else:
        print("Failed to find a suitable segment to insert the node.")
        return None

def tagAdditionalBridgeWays(additionalBridgeWayIds, bridgeId):
    dataSet = getDataSet()
    for wayId in additionalBridgeWayIds:
        way = dataSet.getPrimitiveById(wayId, OsmPrimitiveType.WAY)
        if way:
            tagWayAsBridge(way, bridgeId)
        else:
            print("Additional bridge way %d not found." % wayId)

def processCoordinateSet(coordinateSet):
    dataSet = getDataSet()
    if not dataSet:
        print("No active data set found.")
        return

    points = coordinateSet["points"]
    additionalBridgeWayIds = coordinateSet["additionalBridgeWayIds"]

    bridgeId = coordinateSet["bridgeId"]
    currentPoint = points[0]
    nextPoint = points[0 + 1]

    currentWay = dataSet.getPrimitiveById(currentPoint["wayId"], OsmPrimitiveType.WAY)
    nextWay = dataSet.getPrimitiveById(nextPoint["wayId"], OsmPrimitiveType.WAY)

    if not currentWay or not nextWay:
        print("Way not found for point %d or %d" % (0, 0 + 1))

    if len(additionalBridgeWayIds)== 0:
        # Find common node between the two ways
        commonNode = None
        currentWayNodes = currentWay.getNodes()
        nextWayNodes = nextWay.getNodes()

        if currentWayNodes[0] == nextWayNodes[0] or currentWayNodes[0] == nextWayNodes[-1]:
            commonNode = currentWayNodes[0]
        elif currentWayNodes[-1] == nextWayNodes[0] or currentWayNodes[-1] == nextWayNodes[-1]:
            commonNode = currentWayNodes[-1]

        if currentPoint["latitude"] == -1 and currentPoint["longitude"] == -1:
            tagAdditionalBridgeWays(currentWay, bridgeId)
        else:
            addNodeToWay(currentWay, LatLon(currentPoint["latitude"], currentPoint["longitude"]), True, commonNode, bridgeId)
        if currentPoint["latitude"] == -1 and currentPoint["longitude"] == -1:
            tagAdditionalBridgeWays(nextWay, bridgeId)
        else:    
            addNodeToWay(nextWay, LatLon(nextPoint["latitude"], nextPoint["longitude"]), False, commonNode, bridgeId)
    else:
        # Find common node for current way and additional bridge way
        commonNode = None
        currentWayNodes = currentWay.getNodes()
        additionalBridgeWay = dataSet.getPrimitiveById(additionalBridgeWayIds[0], OsmPrimitiveType.WAY)
        additionalBridgeWayNodes = additionalBridgeWay.getNodes()

        if currentWayNodes[0] == additionalBridgeWayNodes[0] or currentWayNodes[0] == additionalBridgeWayNodes[-1]:
            commonNode = currentWayNodes[0]
        elif currentWayNodes[-1] == additionalBridgeWayNodes[0] or currentWayNodes[-1] == additionalBridgeWayNodes[-1]:
            commonNode = currentWayNodes[-1]
        if currentPoint["latitude"] == -1 and currentPoint["longitude"] == -1:
            addTagCommand = ChangePropertyCommand(currentWay, BRIDGE_TAG, BRIDGE_VALUE)
            UndoRedoHandler.getInstance().add(addTagCommand)
        else:
            addNodeToWay(currentWay, LatLon(currentPoint["latitude"], currentPoint["longitude"]), True, commonNode)

        # Find common node for next way and additional bridge way
        commonNode = None
        nextWayNodes = nextWay.getNodes()
        additionalBridgeWay = dataSet.getPrimitiveById(additionalBridgeWayIds[-1], OsmPrimitiveType.WAY)
        additionalBridgeWayNodes = additionalBridgeWay.getNodes()

        if nextWayNodes[0] == additionalBridgeWayNodes[0] or nextWayNodes[0] == additionalBridgeWayNodes[-1]:
            commonNode = nextWayNodes[0]
        elif nextWayNodes[-1] == additionalBridgeWayNodes[0] or nextWayNodes[-1] == additionalBridgeWayNodes[-1]:
            commonNode = nextWayNodes[-1]
        if currentPoint["latitude"] == -1 and currentPoint["longitude"] == -1:
            addTagCommand = ChangePropertyCommand(nextWay, BRIDGE_TAG, BRIDGE_VALUE)
            UndoRedoHandler.getInstance().add(addTagCommand)
        else:
            addNodeToWay(nextWay, LatLon(nextPoint["latitude"], nextPoint["longitude"]), False, commonNode, bridgeId)

    tagAdditionalBridgeWays(additionalBridgeWayIds, bridgeId)

    MainApplication.getMap().mapView.repaint()

# Main execution
try:
    for coordinateSet in coordinatesList:
        processCoordinateSet(coordinateSet)
except Exception as error:
    print("An error occurred: %s" % str(error))