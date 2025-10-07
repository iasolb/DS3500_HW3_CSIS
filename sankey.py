"""
File: sankey.py
Author: Ian Solberg
Description: reusable sankey builder library
"""

import plotly.graph_objects as go
import plotly.io as pio
import pandas as pd

pio.renderers.default = "browser"


def _code_mapping(df, *cols):
    """
    Helper function to map the data labels to integers
    df: pd.DataFrame
    *cols: column names to encode
    returns: encoded dataframe and labels
    """
    df_copy = df.copy()

    labels = (
        pd.concat([df_copy[col] for col in cols]).unique().tolist()
    )  # Each Unique Label/Category
    nums = range(len(labels))  # Indexes for labels
    mapping_dct = dict(zip(labels, nums))  # Mapping dct

    for col in cols:
        df_copy[col] = df_copy[col].map(mapping_dct)  # map integers to encode

    return df_copy, labels  # return labels


def _column_stacking(df, *cols):
    """
    Stack multiple columns into a source-target format for sankey plotting.
    df: pd.DataFrame
    *cols: column names to stack
    returns: pd.DataFrame with 'src' and 'targ' columns
    """
    stacked_frames = []

    for i in range(len(cols) - 1):  # Iterate through pairs of columns for flows,
        temp = df[[cols[i], cols[i + 1]]].copy()
        temp.columns = ["src", "targ"]  # rename to match other frames
        stacked_frames.append(temp)

    stacked = pd.concat(stacked_frames, axis=0, ignore_index=True)  # stack vertically
    return stacked


def make_sankey(df, *cols, vals=None, **kwargs):
    """
    Generate a sankey diagram from a dataframe.
    df: pd.DataFrame
    *cols: column names for the flow (minimum 2 required)
    vals: str (column name for values) ~ **optional**
    **kwargs: additional keyword arguments for sankey diagram customization
    returns: plotly.graph_objects.Figure
    """
    if len(cols) < 2:
        raise ValueError("Must provide at least source and target columns")

    TwoVar = len(cols) == 2  # Binary, controls stacking function and labels

    if vals:  # val check
        if vals not in df.columns:
            raise ValueError(f"Values column '{vals}' not found in dataframe")
        values = df[vals].tolist()
    else:
        values = [1] * len(df)  # Default flow of 1

    df_encoded, labels = _code_mapping(df, *cols)

    if TwoVar:  # Binary case, no stacking needed
        src, targ = cols[0], cols[1]
        link = {
            "source": df_encoded[src].tolist(),
            "target": df_encoded[targ].tolist(),
            "value": values,
        }
    else:  # Multi-var case, apply stacking function
        encoded_df_stacked = _column_stacking(df_encoded, *cols)

        if vals:
            num_layers = len(cols) - 1
            stacked_values = values * num_layers  # repeat vals for each layer
        else:
            stacked_values = [1] * len(encoded_df_stacked)  # Default flow of 1

        link = {
            "source": encoded_df_stacked["src"].tolist(),
            "target": encoded_df_stacked["targ"].tolist(),
            "value": stacked_values,
        }
    # Get title kwarg if there otherwise default title logic applied:
    title = kwargs.get("title", None)
    if not title:  # default title logic
        if TwoVar:
            title = f"Flow from {cols[0]} to {cols[1]}"
        else:
            title = f"Flow between {', '.join(cols)}"

    # Get Kwargs for Plotly Sankey Customization:
    thickness = kwargs.get("thickness", 20)
    font_size = kwargs.get("font_size", 8)
    pad = kwargs.get("pad", 15)
    line_color = kwargs.get("line_color", "black")
    line_width = kwargs.get("line_width", 0)
    link["line"] = {"color": line_color, "width": line_width}

    # TODO add more customization options

    # Build Node
    node = {
        "label": labels,
        "pad": pad,
        "thickness": thickness,
    }

    # diagram height and width

    diagram_height = kwargs.get("height", 800)
    diagram_width = kwargs.get("width", 1200)
    # Build fig:
    sk = go.Sankey(link=link, node=node)
    fig = go.Figure(sk)
    fig.update_layout(
        title_text=title,
        font_size=font_size,
        height=diagram_height,
        width=diagram_width,
    )

    return fig


def show_sankey(df, *cols, vals=None, png=None, **kwargs):
    """
    Display a sankey diagram.
    Optionally save to PNG
    """
    fig = make_sankey(df, *cols, vals=vals, **kwargs)
    fig.show()
    if png:
        fig.write_image(png)
