import panel as pn


# Loads javascript dependencies and configures Panel (required)
pn.extension()


# WIDGET DECLARATIONS

# Search Widgets


# Plotting widgets


# CALLBACK FUNCTIONS


# CALLBACK BINDINGS (Connecting widgets to callback functions)


# DASHBOARD WIDGET CONTAINERS ("CARDS")

card_width = 320

search_card = pn.Card(
    pn.Column(
        # Widget 1
        # Widget 2
        # Widget 3
    ),
    title="Search",
    width=card_width,
    collapsed=False,
)


plot_card = pn.Card(
    pn.Column(
        # Widget 1
        # Widget 2
        # Widget 3
    ),
    title="Plot",
    width=card_width,
    collapsed=True,
)


# LAYOUT

layout = pn.template.FastListTemplate(
    title="Dashboard Title Goes Here",
    sidebar=[
        search_card,
        plot_card,
    ],
    theme_toggle=False,
    main=[
        pn.Tabs(
            ("Tab1", None),  # Replace None with callback binding
            ("Tab2", None),  # Replace None with callback binding
            active=1,  # Which tab is active by default?
        )
    ],
    header_background="#a93226",
).servable()

layout.show()
