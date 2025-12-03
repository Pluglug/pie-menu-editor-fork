# Configuration file for the Sphinx documentation builder.
# This is an EXAMPLE - adapt to your actual docs repository

# -- Project information -----------------------------------------------------
project = 'PME Architecture'
copyright = '2024, Pluglug'
author = 'Pluglug'

# -- General configuration ---------------------------------------------------
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.viewcode',
    'sphinx.ext.napoleon',
    'sphinx_design',           # Cards, tabs, grids
    'sphinxcontrib.mermaid',   # Mermaid diagrams
    'sphinx_copybutton',       # Copy button for code blocks
]

# Mermaid configuration
mermaid_version = "10.6.1"
mermaid_init_js = """
mermaid.initialize({
    startOnLoad: true,
    theme: 'dark',
    themeVariables: {
        primaryColor: '#58a6ff',
        primaryTextColor: '#c9d1d9',
        primaryBorderColor: '#30363d',
        lineColor: '#8b949e',
        secondaryColor: '#21262d',
        tertiaryColor: '#161b22'
    }
});
"""

# -- Options for HTML output -------------------------------------------------
html_theme = 'furo'  # or 'sphinx_rtd_theme', 'pydata_sphinx_theme'

html_theme_options = {
    # Furo theme options
    "dark_css_variables": {
        "color-brand-primary": "#58a6ff",
        "color-brand-content": "#58a6ff",
    },
}

# -- Extension configuration -------------------------------------------------
# Napoleon settings
napoleon_google_docstring = True
napoleon_numpy_docstring = True

# sphinx-design settings
sd_fontawesome_latex = True

# -- Options for autodoc -----------------------------------------------------
autodoc_member_order = 'bysource'
autodoc_typehints = 'description'
