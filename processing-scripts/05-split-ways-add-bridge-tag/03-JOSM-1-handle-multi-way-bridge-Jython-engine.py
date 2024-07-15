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


coordinatesList = [
    {
        "points": [
            {"latitude": 36.6490109994807, "longitude": -89.06306871832646, "wayId": 16208279},
            {"latitude": 36.649008842327014, "longitude": -89.06324527869246, "wayId": 16208919},
        ],
        "additionalBridgeWayIds": []
    }
]


def getDataSet():
    return MainApplication.getLayerManager().getEditDataSet()

def addNodeToWay(way, latLon, isFirstPoint, preExistingNodeId):
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
                isBridgeWay = (selectedWayNodes[0].getId() == closestNode.getId() and selectedWayNodes[-1].getId() == preExistingNodeId) or (selectedWayNodes[-1].getId() == closestNode.getId() and selectedWayNodes[0].getId() == preExistingNodeId)
            else:
                isBridgeWay = (selectedWayNodes[0].getId() == preExistingNodeId and selectedWayNodes[-1].getId() == closestNode.getId()) or (selectedWayNodes[-1].getId() == preExistingNodeId and selectedWayNodes[0].getId() == closestNode.getId())

            if isBridgeWay:
                addTagCommand = ChangePropertyCommand(selectedWay, BRIDGE_TAG, BRIDGE_VALUE)
                UndoRedoHandler.getInstance().add(addTagCommand)
                print("Bridge way %d tagged successfully." % selectedWay.getId())
                break

        return closestNode
    else:
        print("Failed to find a suitable segment to insert the node.")
        return None

def tagAdditionalBridgeWays(additionalBridgeWayIds):
    dataSet = getDataSet()
    for wayId in additionalBridgeWayIds:
        way = dataSet.getPrimitiveById(wayId, OsmPrimitiveType.WAY)
        if way:
            addTagCommand = ChangePropertyCommand(way, BRIDGE_TAG, BRIDGE_VALUE)
            UndoRedoHandler.getInstance().add(addTagCommand)
            print("Additional bridge way %d tagged successfully." % wayId)
        else:
            print("Additional bridge way %d not found." % wayId)

def processCoordinateSet(coordinateSet):
    dataSet = getDataSet()
    if not dataSet:
        print("No active data set found.")
        return

    points = coordinateSet["points"]
    additionalBridgeWayIds = coordinateSet["additionalBridgeWayIds"]

    
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

        if currentWayNodes[0].getId() == nextWayNodes[0].getId() or currentWayNodes[0].getId() == nextWayNodes[-1].getId():
            commonNode = currentWayNodes[0]
        elif currentWayNodes[-1].getId() == nextWayNodes[0].getId() or currentWayNodes[-1].getId() == nextWayNodes[-1].getId():
            commonNode = currentWayNodes[-1]

        addNodeToWay(currentWay, LatLon(currentPoint["latitude"], currentPoint["longitude"]), True, commonNode.getId())
        
        addNodeToWay(nextWay, LatLon(nextPoint["latitude"], nextPoint["longitude"]), False, commonNode.getId())
    else:
        # Find common node for current way and additional bridge way
        commonNode = None
        currentWayNodes = currentWay.getNodes()
        additionalBridgeWay = dataSet.getPrimitiveById(additionalBridgeWayIds[0], OsmPrimitiveType.WAY)
        additionalBridgeWayNodes = additionalBridgeWay.getNodes()

        if currentWayNodes[0].getId() == additionalBridgeWayNodes[0].getId() or currentWayNodes[0].getId() == additionalBridgeWayNodes[-1].getId():
            commonNode = currentWayNodes[0]
        elif currentWayNodes[-1].getId() == additionalBridgeWayNodes[0].getId() or currentWayNodes[-1].getId() == additionalBridgeWayNodes[-1].getId():
            commonNode = currentWayNodes[-1]
        
        addNodeToWay(currentWay, LatLon(currentPoint["latitude"], currentPoint["longitude"]), True, commonNode.getId())

        # Find common node for next way and additional bridge way
        commonNode = None
        nextWayNodes = nextWay.getNodes()
        additionalBridgeWay = dataSet.getPrimitiveById(additionalBridgeWayIds[-1], OsmPrimitiveType.WAY)
        additionalBridgeWayNodes = additionalBridgeWay.getNodes()

        if nextWayNodes[0].getId() == additionalBridgeWayNodes[0].getId() or nextWayNodes[0].getId() == additionalBridgeWayNodes[-1].getId():
            commonNode = nextWayNodes[0]
        elif nextWayNodes[-1].getId() == additionalBridgeWayNodes[0].getId() or nextWayNodes[-1].getId() == additionalBridgeWayNodes[-1].getId():
            commonNode = nextWayNodes[-1]

        addNodeToWay(nextWay, LatLon(nextPoint["latitude"], nextPoint["longitude"]), False, commonNode.getId())

    tagAdditionalBridgeWays(additionalBridgeWayIds)

    MainApplication.getMap().mapView.repaint()

# Main execution
try:
    for coordinateSet in coordinatesList:
        processCoordinateSet(coordinateSet)
except Exception as error:
    print("An error occurred: %s" % str(error))