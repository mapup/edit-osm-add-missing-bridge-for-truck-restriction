import * as console from "josm/scriptingconsole";

const LatLon = Java.type("org.openstreetmap.josm.data.coor.LatLon");
const Node = Java.type("org.openstreetmap.josm.data.osm.Node");
const Way = Java.type("org.openstreetmap.josm.data.osm.Way");
const MainApplication = Java.type("org.openstreetmap.josm.gui.MainApplication");
const SplitWayAction = Java.type("org.openstreetmap.josm.actions.SplitWayAction");
const AddCommand = Java.type("org.openstreetmap.josm.command.AddCommand");
const ChangeCommand = Java.type("org.openstreetmap.josm.command.ChangeCommand");
const Geometry = Java.type("org.openstreetmap.josm.tools.Geometry");
const ProjectionRegistry = Java.type("org.openstreetmap.josm.data.projection.ProjectionRegistry");
const UndoRedoHandler = Java.type("org.openstreetmap.josm.data.UndoRedoHandler");
const OsmPrimitiveType = Java.type("org.openstreetmap.josm.data.osm.OsmPrimitiveType");
const ChangePropertyCommand = Java.type("org.openstreetmap.josm.command.ChangePropertyCommand");

console.clear();

// Constants
const BRIDGE_TAG = "bridge";
const BRIDGE_VALUE = "yes";

// Improved coordinate list structure
const coordinatesList = [
  {
    points: [
      { latitude: 36.6490109994807, longitude: -89.06306871832646, wayId: 16208279 },
      { latitude: 36.649008842327014, longitude: -89.06324527869246, wayId: 16208919 },
    ],
    additionalBridgeWayIds: []
  }
];

function getDataSet() {
  return MainApplication.getLayerManager().getEditDataSet();
}

function addNodeToWay(way, latLon, isFirstPoint, preExistingNodeId) {
  const dataSet = getDataSet();
  const projection = ProjectionRegistry.getProjection();
  const wayNodes = way.getNodes();
  let closestIndex = -1;
  let closestDistance = Infinity;
  let closestLatLon = latLon;

  for (let i = 0; i < wayNodes.size() - 1; i++) {
    const segmentStart = projection.latlon2eastNorth(wayNodes.get(i).getCoor());
    const segmentEnd = projection.latlon2eastNorth(wayNodes.get(i + 1).getCoor());
    const point = Geometry.closestPointToSegment(
      segmentStart,
      segmentEnd,
      projection.latlon2eastNorth(latLon)
    );
    const pointLatLon = projection.eastNorth2latlon(point);
    const distance = latLon.greatCircleDistance(pointLatLon);
    if (distance < closestDistance) {
      closestDistance = distance;
      closestIndex = i;
      closestLatLon = pointLatLon;
    }
  }

  if (closestIndex !== -1) {
    const closestNode = new Node(closestLatLon);
    const newWayNodes = new java.util.ArrayList(wayNodes);
    newWayNodes.add(closestIndex + 1, closestNode);

    const newWay = new Way(way);
    newWay.setNodes(newWayNodes);

    UndoRedoHandler.getInstance().add(new AddCommand(dataSet, closestNode));
    UndoRedoHandler.getInstance().add(new ChangeCommand(way, newWay));

    dataSet.setSelected(closestNode);
    SplitWayAction.runOn(dataSet);

    console.println(`Node added at latitude: ${latLon.lat()}, longitude: ${latLon.lon()} and Node ID: ${closestNode.getId()}`);

    // Tag the appropriate way as a bridge
    const selectedWays = dataSet.getSelectedWays();
    for (const selectedWay of selectedWays) {
      const selectedWayNodes = selectedWay.getNodes();
      let isBridgeWay = false;

      if (isFirstPoint) {
        isBridgeWay = (selectedWayNodes.get(0).getId() === closestNode.getId() && selectedWayNodes.get(selectedWayNodes.size() - 1).getId() === preExistingNodeId) ||
                      (selectedWayNodes.get(selectedWayNodes.size() - 1).getId() === closestNode.getId() && selectedWayNodes.get(0).getId() === preExistingNodeId);
      } else {
        isBridgeWay = (selectedWayNodes.get(0).getId() === preExistingNodeId && selectedWayNodes.get(selectedWayNodes.size() - 1).getId() === closestNode.getId()) ||
                      (selectedWayNodes.get(selectedWayNodes.size() - 1).getId() === preExistingNodeId && selectedWayNodes.get(0).getId() === closestNode.getId());
      }

      if (isBridgeWay) {
        const addTagCommand = new ChangePropertyCommand(selectedWay, BRIDGE_TAG, BRIDGE_VALUE);
        UndoRedoHandler.getInstance().add(addTagCommand);
        console.println(`Bridge way ${selectedWay.getId()} tagged successfully.`);
        break;
      }
    }

    return closestNode;
  } else {
    console.println("Failed to find a suitable segment to insert the node.");
    return null;
  }
}

function tagAdditionalBridgeWays(additionalBridgeWayIds) {
  const dataSet = getDataSet();
  for (const wayId of additionalBridgeWayIds) {
    const way = dataSet.getPrimitiveById(wayId, OsmPrimitiveType.WAY);
    if (way) {
      const addTagCommand = new ChangePropertyCommand(way, BRIDGE_TAG, BRIDGE_VALUE);
      UndoRedoHandler.getInstance().add(addTagCommand);
      console.println(`Additional bridge way ${wayId} tagged successfully.`);
    } else {
      console.println(`Additional bridge way ${wayId} not found.`);
    }
  }
}

function processCoordinateSet(coordinateSet) {
  const dataSet = getDataSet();
  if (!dataSet) {
    console.println("No active data set found.");
    return;
  }

  const { points, additionalBridgeWayIds } = coordinateSet;

  const currentPoint = points[0];
  const nextPoint = points[1];

  const currentWay = dataSet.getPrimitiveById(currentPoint.wayId, OsmPrimitiveType.WAY);
  const nextWay = dataSet.getPrimitiveById(nextPoint.wayId, OsmPrimitiveType.WAY);

  if (!currentWay || !nextWay) {
    console.println(`Way not found for point 0 or 1`);
    return;
  }

  if (additionalBridgeWayIds.length === 0) {
    // Find common node between the two ways
    let commonNode = null;
    const currentWayNodes = currentWay.getNodes();
    const nextWayNodes = nextWay.getNodes();

    if (currentWayNodes.get(0).getId() === nextWayNodes.get(0).getId() || currentWayNodes.get(0).getId() === nextWayNodes.get(nextWayNodes.size() - 1).getId()) {
      commonNode = currentWayNodes.get(0);
    } else if (currentWayNodes.get(currentWayNodes.size() - 1).getId() === nextWayNodes.get(0).getId() || currentWayNodes.get(currentWayNodes.size() - 1).getId() === nextWayNodes.get(nextWayNodes.size() - 1).getId()) {
      commonNode = currentWayNodes.get(currentWayNodes.size() - 1);
    }

    addNodeToWay(currentWay, new LatLon(currentPoint.latitude, currentPoint.longitude), true, commonNode.getId());
    addNodeToWay(nextWay, new LatLon(nextPoint.latitude, nextPoint.longitude), false, commonNode.getId());
  } else {
    // Find common node for current way and additional bridge way
    let commonNode = null;
    const currentWayNodes = currentWay.getNodes();
    const additionalBridgeWay = dataSet.getPrimitiveById(additionalBridgeWayIds[0], OsmPrimitiveType.WAY);
    const additionalBridgeWayNodes = additionalBridgeWay.getNodes();

    if (currentWayNodes.get(0).getId() === additionalBridgeWayNodes.get(0).getId() || currentWayNodes.get(0).getId() === additionalBridgeWayNodes.get(additionalBridgeWayNodes.size() - 1).getId()) {
      commonNode = currentWayNodes.get(0);
    } else if (currentWayNodes.get(currentWayNodes.size() - 1).getId() === additionalBridgeWayNodes.get(0).getId() || currentWayNodes.get(currentWayNodes.size() - 1).getId() === additionalBridgeWayNodes.get(additionalBridgeWayNodes.size() - 1).getId()) {
      commonNode = currentWayNodes.get(currentWayNodes.size() - 1);
    }
    
    addNodeToWay(currentWay, new LatLon(currentPoint.latitude, currentPoint.longitude), true, commonNode.getId());

    // Find common node for next way and additional bridge way
    commonNode = null;
    const nextWayNodes = nextWay.getNodes();
    const lastAdditionalBridgeWay = dataSet.getPrimitiveById(additionalBridgeWayIds[additionalBridgeWayIds.length - 1], OsmPrimitiveType.WAY);
    const lastAdditionalBridgeWayNodes = lastAdditionalBridgeWay.getNodes();

    if (nextWayNodes.get(0).getId() === lastAdditionalBridgeWayNodes.get(0).getId() || nextWayNodes.get(0).getId() === lastAdditionalBridgeWayNodes.get(lastAdditionalBridgeWayNodes.size() - 1).getId()) {
      commonNode = nextWayNodes.get(0);
    } else if (nextWayNodes.get(nextWayNodes.size() - 1).getId() === lastAdditionalBridgeWayNodes.get(0).getId() || nextWayNodes.get(nextWayNodes.size() - 1).getId() === lastAdditionalBridgeWayNodes.get(lastAdditionalBridgeWayNodes.size() - 1).getId()) {
      commonNode = nextWayNodes.get(nextWayNodes.size() - 1);
    }

    addNodeToWay(nextWay, new LatLon(nextPoint.latitude, nextPoint.longitude), false, commonNode.getId());
  }

  tagAdditionalBridgeWays(additionalBridgeWayIds);

  MainApplication.getMap().mapView.repaint();
}

// Main execution
try {
  for (const coordinateSet of coordinatesList) {
    processCoordinateSet(coordinateSet);
  }
} catch (error) {
  console.println(`An error occurred: ${error.message}`);
}