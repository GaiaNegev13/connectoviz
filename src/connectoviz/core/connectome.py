# connectoviz/core/connectome.py

import numpy as np
import pandas as pd
from typing import Union, Dict, List, Optional, Any
from connectoviz.io.parsers import (
    parse_matrix,
    masking,
    check_metadata,
    check_mapping,
    compare_mapping,
    atlas_check,
    merge_metadata,
)
from connectoviz.utils.handle_layout_prefrences import (
    handle_layout,
    handle_layers,
)

# next line commented out so pre commit wont kill me
# from connectoviz.utils.validation import validate_connectome_inputs


# 1.07.25- ideas for improvements:
# - add a method to convert the connectome to a networkx graph
# - use @property @setter and so on to encapsulate diffrent funcions and attributes as properties


class Connectome:
    """
    Internal data structure to store parsed connectome info.

    Parameters
    ----------
    con_mat : array-like
        Connectivity matrix (square 2D structure).
    node_metadata : dict or DataFrame
        Metadata table (e.g. lobe, hemisphere, etc.).
    atlas : str
        Atlas name (e.g. 'Schaefer100').
    """

    def __init__(
        self,
        con_mat: Union[np.ndarray, pd.DataFrame, List[List[float]], str],
        atlas: Optional[str] = None,
        node_metadata: Union[pd.DataFrame, Dict[str, List], str] = None,
        mapping: Optional[
            Union[Dict[str, str], pd.DataFrame]
        ] = None,  # verse 1 for mapping
        node_vec: Optional[Union[List[str], np.ndarray]] = None,
        label_vec: Optional[Union[List[str], np.ndarray]] = None,  # verse 2 for mapping
        # when no mapping is provided, we can use index_col and label_col to specify the columns in the metadata
        index_col: Optional[str] = None,
        label_col: Optional[str] = None,
    ):
        self.con_mat: np.ndarray = parse_matrix(con_mat)
        self.atlas: pd.DataFrame = atlas
        self.node_metadata: pd.DataFrame = self._process_metadata(node_metadata)
        self.mapping, self.index_col, self.label_col = self._validate_maps(
            mapping, node_vec, label_vec, index_col, label_col
        )
        self.merged_metadata: Optional[pd.DataFrame] = self._apply_merge()

    def _process_metadata(self, metadata):
        # Your logic for checking and standardizing metadata
        if metadata is None:
            return None
        # Assuming `atlas` is already loaded and validated

        return check_metadata(metadata, atlas=self.atlas, mapping=self.mapping)

    def _apply_merge(self):
        """
        use the merge_metadata function to merge the atlas with metadata
        """
        if self.node_metadata is None or self.node_metadata.empty:
            raise ValueError("Node metadata is not specified or empty.")
        if self.atlas is None or self.atlas.empty:
            raise ValueError("Atlas is not specified or empty.")
        # merge the metadata with the atlas and get the number of nodes from con_mat
        if self.con_mat is None or self.con_mat.size == 0:
            raise ValueError("Connectivity matrix is not specified or empty.")
        # Check if the number of nodes in the metadata matches the connectivity matrix
        if self.node_metadata.shape[0] != self.con_mat.shape[0]:
            raise ValueError(
                "Node metadata does not match the number of nodes in the connectivity matrix."
            )
        combined_metadata = merge_metadata(
            self.atlas, self.node_metadata, self.con_mat.shape[0].astype(int)
        )

        return combined_metadata

    def _validate_maps(
        self,
        mapping: Optional[Union[Dict[str, str], pd.DataFrame]],
        node_vec: Optional[Union[List[str], np.ndarray]] = None,
        label_vec: Optional[Union[List[str], np.ndarray]] = None,
        index_col: Optional[str] = None,
        label_col: Optional[str] = None,
    ):
        if mapping is not None:
            # Validate mapping structure
            validated_mapping = check_mapping(mapping, node_vec, label_vec)

            # Check mapping values against atlas
            _, label_col_r = compare_mapping(validated_mapping, self.atlas)
            # validate them and the atlas on the way:
            _, validated_index_col, validated_label_col = atlas_check(
                self.atlas, index_col, label_col_r
            )
            return mapping, validated_index_col, validated_label_col

    # create a method to create  connnectom named
    # add a function from_input to create a Connectome from inputs
    # functions assumes con_mat is a square 2D structure, atlas is a DataFrame, and node_metadata is a DataFrame
    # and mapping is an optional dict or DataFrame
    @classmethod
    def from_inputs(
        cls,
        con_mat: np.ndarray,
        atlas: pd.DataFrame,
        node_metadata: Optional[pd.DataFrame],
        mapping: Optional[Union[Dict[str, str], pd.DataFrame]] = None,
    ):
        """
        Create a Connectome instance from input parameters.

        Parameters
        ----------
        con_mat : array-like
            Connectivity matrix (square 2D structure).
        atlas : pd.DataFrame
            Atlas reference table.
        node_metadata : pd.DataFrame
            Node-level metadata (same length as con_mat).
        mapping : dict or DataFrame, optional
            Optional remapping of node indices to labels.

        Returns
        -------
        Connectome
            A Connectome instance.
        """

        # check mapping

        # Validate and process the atlas
        atlas_bool, _, _ = atlas_check(atlas)
        if not atlas_bool:
            raise ValueError("Atlas is not valid or empty.")

        return Connectome(
            con_mat=con_mat,
            atlas=atlas,
            node_metadata=node_metadata,
            mapping=mapping,
        )

    def reorder_nodes(self, layout_dict: Dict[str, Any]):
        """
        Reorder the connectivity matrix by indicated input.
        Parameters
        ----------
        layout_dict : dict
            Dictionary containing layout preferences. It can include:
            - 'hemi': bool, whether to reorder by hemisphere.
            - 'other': bool, whether to include nodes not grouped by the specified hemisphere.
            - 'grouping': str, metadata column to group nodes by.
            - 'display_node_names': bool, whether to display node names.
            - 'display_group_names': bool, whether to display group names.
        Returns
        h



        """
        # dfs_and_more=handle_layout
        handled_nodes, _, _, _ = handle_layout(self.node_metadata, layout_dict)
        # set the handeled nodes as the merged metadata
        self.merged_metadata = handled_nodes

    def apply_layers(self, layers_list: List[str]):
        """
        Apply layers to the connectivity matrix based on the provided layers list.
        for know- just filtering the metadata based on it
        Parameters
        ----------
        layers_list : list
            List of metadata columns to apply as layers.
        Returns
        -------
        """
        if self.merged_metadata is None or self.merged_metadata.empty:
            raise ValueError("Merged metadata is not specified or empty.")
        # check if the layers_list is valid
        gilterd_metadata = handle_layers(self.merged_metadata, layers_list)
        if gilterd_metadata is None or gilterd_metadata.empty:
            raise ValueError("Filtered metadata is not specified or empty.")

        self.merged_metadata = gilterd_metadata

    def to_numpy(self):
        return self.con_mat.copy()

    def to_dataframe(self):
        # Convert the connectivity matrix to a DataFrame with node metadata as index and columns.
        if self.node_metadata is None or self.node_metadata.empty:
            raise ValueError("Node metadata is not specified or empty.")
        return pd.DataFrame(
            self.con_mat,
            index=self.node_metadata.index,
            columns=self.node_metadata.index,
        )

    def apply_mask(self, mask: Union[np.ndarray, List[bool]]):
        """
        Apply a binary mask to the connectivity matrix.

        Parameters
        ----------
        mask : array-like
            Binary mask to apply to the connectivity matrix.
        """
        self.con_mat = masking(self.con_mat, mask)

    def summary(self):
        return (
            f"Atlas: {self.atlas or 'unspecified'}\n"
            f"Nodes: {self.con_mat.shape[0]}\n"
            f"Metadata: {list(self.node_metadata.columns or "none specified")}\n"
            f"\nMapping: {self.mapping or 'none specified'}\n"
            f"Index Column: {self.index_col or 'none specified'}\n"
            f"Label Column: {self.label_col or 'none specified'}"
        )
