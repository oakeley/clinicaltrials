"""
Module for building and managing relationship graphs from spreadsheet data.
"""

import logging
from typing import Dict, List, Any, Set


class RelationshipGraph:
    """
    Manages relationships between entities extracted from spreadsheet data.
    """

    def __init__(self):
        """
        Initialize an empty relationship graph.
        """
        self.nodes = {}
        self.edges = []
        self.logger = logging.getLogger(__name__)

    def add_node(self, node_id: str, node_type: str, attributes: Dict[str, Any]) -> None:
        """
        Add a node to the graph.

        Args:
            node_id: Unique identifier for the node
            node_type: Type of the node
            attributes: Dictionary of node attributes
        """
        if node_id not in self.nodes:
            self.nodes[node_id] = {
                'type': node_type,
                'attributes': attributes
            }
            self.logger.debug(f"Added node: {node_id} of type {node_type}")

    def add_edge(self, source_id: str, target_id: str, relationship: str) -> None:
        """
        Add a directed edge between two nodes.

        Args:
            source_id: Source node identifier
            target_id: Target node identifier
            relationship: Type of relationship
        """
        edge = {
            'source': source_id,
            'target': target_id,
            'relationship': relationship
        }
        self.edges.append(edge)
        self.logger.debug(f"Added edge: {source_id} -> {target_id} ({relationship})")

    def build_from_structured_data(self, structured_data: Dict[str, Any]) -> None:
        """
        Build graph from structured spreadsheet data.

        Args:
            structured_data: Dictionary of sheet data with headers and rows
        """
        self.logger.info("Building relationship graph from structured data")

        for sheet_name, sheet_data in structured_data.items():
            headers = sheet_data.get('headers', [])
            rows = sheet_data.get('rows', [])

            self.logger.info(f"Processing sheet: {sheet_name} with {len(rows)} rows")

            for idx, row in enumerate(rows):
                node_id = f"{sheet_name}_{idx}"
                self.add_node(node_id, sheet_name, row)

                self._identify_relationships(node_id, sheet_name, row, structured_data)

        self.logger.info(f"Graph built with {len(self.nodes)} nodes and {len(self.edges)} edges")

    def _identify_relationships(self, node_id: str, sheet_name: str,
                               row: Dict[str, Any], all_data: Dict[str, Any]) -> None:
        """
        Identify and create relationships between nodes based on data patterns.

        Args:
            node_id: Current node identifier
            sheet_name: Name of the current sheet
            row: Current row data
            all_data: All structured data for cross-referencing
        """
        for key, value in row.items():
            if not value:
                continue

            for other_sheet, other_data in all_data.items():
                if other_sheet == sheet_name:
                    continue

                for other_idx, other_row in enumerate(other_data.get('rows', [])):
                    for other_key, other_value in other_row.items():
                        if value == other_value and value.strip():
                            other_node_id = f"{other_sheet}_{other_idx}"
                            relationship = f"{key}_matches_{other_key}"
                            self.add_edge(node_id, other_node_id, relationship)

    def get_nodes_by_type(self, node_type: str) -> List[Dict[str, Any]]:
        """
        Retrieve all nodes of a specific type.

        Args:
            node_type: Type of nodes to retrieve

        Returns:
            List of nodes with their attributes
        """
        return [
            {'id': node_id, **node_data}
            for node_id, node_data in self.nodes.items()
            if node_data['type'] == node_type
        ]

    def get_connected_nodes(self, node_id: str) -> List[str]:
        """
        Get all nodes connected to a given node.

        Args:
            node_id: Node identifier

        Returns:
            List of connected node identifiers
        """
        connected = set()

        for edge in self.edges:
            if edge['source'] == node_id:
                connected.add(edge['target'])
            elif edge['target'] == node_id:
                connected.add(edge['source'])

        return list(connected)

    def to_dict(self) -> Dict[str, Any]:
        """
        Export graph as a dictionary.

        Returns:
            Dictionary representation of the graph
        """
        return {
            'nodes': self.nodes,
            'edges': self.edges,
            'statistics': {
                'node_count': len(self.nodes),
                'edge_count': len(self.edges)
            }
        }

    def extract_search_terms(self) -> Set[str]:
        """
        Extract unique search terms from all node attributes.

        Returns:
            Set of unique non-empty attribute values
        """
        search_terms = set()

        for node_data in self.nodes.values():
            attributes = node_data.get('attributes', {})
            for value in attributes.values():
                if value and isinstance(value, str) and value.strip():
                    search_terms.add(value.strip())

        self.logger.info(f"Extracted {len(search_terms)} unique search terms")
        return search_terms
