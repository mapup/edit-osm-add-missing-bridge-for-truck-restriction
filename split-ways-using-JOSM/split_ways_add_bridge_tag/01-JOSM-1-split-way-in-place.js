import * as console from "josm/scriptingconsole";
const LatLon = Java.type("org.openstreetmap.josm.data.coor.LatLon");
const Node = Java.type("org.openstreetmap.josm.data.osm.Node");
const Way = Java.type("org.openstreetmap.josm.data.osm.Way");
const MainApplication = Java.type("org.openstreetmap.josm.gui.MainApplication");
const SplitWayAction = Java.type(
  "org.openstreetmap.josm.actions.SplitWayAction"
);
const AddCommand = Java.type("org.openstreetmap.josm.command.AddCommand");
const SplitWayCommand = Java.type(
  "org.openstreetmap.josm.command.SplitWayCommand"
);
const ChangeCommand = Java.type("org.openstreetmap.josm.command.ChangeCommand");
const SequenceCommand = Java.type(
  "org.openstreetmap.josm.command.SequenceCommand"
);
const Geometry = Java.type("org.openstreetmap.josm.tools.Geometry");
const ProjectionRegistry = Java.type(
  "org.openstreetmap.josm.data.projection.ProjectionRegistry"
);
const ArrayList = Java.type("java.util.ArrayList");
const UndoRedoHandler = Java.type(
  "org.openstreetmap.josm.data.UndoRedoHandler"
);
const OsmPrimitiveType = Java.type(
  "org.openstreetmap.josm.data.osm.OsmPrimitiveType"
);
console.clear();
// List of coordinates with way IDs
const coordinatesList = [
  [
    { latitude: 36.99063067649576, longitude: -85.90225171619728, way_id: 108707726 },
    { latitude: 36.990448735147304, longitude: -85.90199932269573, way_id: 108707726 },
  ],
  [
    { latitude: 36.98806513790712, longitude: -85.90708744181889, way_id: 16082992 },
    { latitude: 36.987918964647626, longitude: -85.90690103566203, way_id: 16082992 },
  ],
];

const dataSet = MainApplication.getLayerManager().getEditDataSet();
if (dataSet !== null) {
  // Assume only one way is selected
  for (const coordinates of coordinatesList) {
    var bridgeEndId = -1;
    var bridgeStartId = -1;
    for (var i = 0; i < coordinates.length; i++) {
      const coord = coordinates[i];
      // Get the selected way by its ID
      const selectedWay = dataSet.getPrimitiveById(
        coord.way_id,
        OsmPrimitiveType.WAY
      );
      const latLon = new LatLon(coord.latitude, coord.longitude);
      let closestLatLon = new LatLon(coord.latitude, coord.longitude);
      const projection = ProjectionRegistry.getProjection();
      const wayNodes = selectedWay.getNodes();
      let closestIndex = -1;
      let closestDistance = Infinity;
      // Find the closest point on the way to the given coordinate
      for (let i = 0; i < wayNodes.size() - 1; i++) {
        const segmentStart = projection.latlon2eastNorth(
          wayNodes.get(i).getCoor()
        );
        const segmentEnd = projection.latlon2eastNorth(
          wayNodes.get(i + 1).getCoor()
        );
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
        // console.println(closestNode);
        const newWayNodes = new java.util.ArrayList(wayNodes);
        if (i == 0) {
          bridgeStartId = closestNode.getId();
        }
        if (i == coordinates.length - 1) {
          bridgeEndId = closestNode.getId();
        }
        newWayNodes.add(closestIndex + 1, closestNode);

        // Create a new way with the updated node array
        const newWay = new Way(selectedWay);
        newWay.setNodes(newWayNodes);

        // Add the new node to the data set and update the way
        const addCommand = new AddCommand(dataSet, closestNode);
        UndoRedoHandler.getInstance().add(addCommand);
        const changeCommand = new ChangeCommand(selectedWay, newWay);
        UndoRedoHandler.getInstance().add(changeCommand);
        const nodeArray = Java.to(
          [closestNode],
          "org.openstreetmap.josm.data.osm.Node[]"
        );
        dataSet.setSelected(closestNode);
        SplitWayAction.runOn(dataSet);

        // Repaint the map to reflect changes
        MainApplication.getMap().mapView.repaint();

        console.println(
          `Node added at latitude: ${coord.latitude}, longitude: ${coord.longitude} and way updated.`
        );
      } else {
        console.println(
          "Failed to find a suitable segment to insert the node."
        );
      }
    }
    // After your loop ends
    console.println("Attempting to find and tag bridge way...");

    // Assuming there's a direct way connecting bridgeStartId and bridgeEndId among the selected ways
    let bridgeWay = null;

    // Get all selected ways
    const selectedWays = dataSet.getSelectedWays();

    // Iterate over all selected ways
    for (const way of selectedWays) {
      let isBridgeWay = true;
      let currentNodeId = bridgeStartId;

      // Check if the way contains both start and end nodes in sequence
      for (const nodeId of way.getNodes().map((node) => node.getId())) {
        if (nodeId === currentNodeId) {
          currentNodeId = nodeId;
          if (currentNodeId === bridgeEndId) break; // Reached end, it's our way
        } else {
          isBridgeWay = false; // Sequence broken, not our way
          break;
        }
      }

      if (isBridgeWay && currentNodeId === bridgeEndId) {
        bridgeWay = way;
        break;
      }
    }

    if (bridgeWay) {
      // Tag the identified way as a bridge
      bridgeWay.put("bridge", "yes");

      // Apply the change
      const changeBridgeTagCommand = new ChangeCommand(bridgeWay, bridgeWay);
      UndoRedoHandler.getInstance().add(changeBridgeTagCommand);

      console.println("Bridge way tagged successfully.");
    } else {
      console.println(
        "Could not identify a unique way among the selected ones connecting the specified nodes as a bridge."
      );
    }
  }
}
