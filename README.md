# TextTUI

TextTUI is a set of extensions to the Textual and Textual-Inputs libraries.  Currently a **Work in Progress** that is based on the 0.1.14 branch of Textual.

> **NOTE:** The 0.1.14 branch of Textual is the "early adopter" branch and will eventually be replaced with a "ccs" branch.  At that point, this library will be in-compatible until appropriate updates are made to this repo.

> **DISCLAIMER:** I have been writing C/C++ code since 1986, but Python code only since November, 2021!  I know this project is not packaged in a standard "Python way" ... I am still learning / trying to figure out how to do that.  Take it for what it is.

![screenshot](./imgs/texttui.png)

## Installation

As mentioned in my disclaimer, I am still very new to Python and haven't yet trained myself how to create appropriate packages to specify dependencies or use 'pip install'.  For now, simply install the required dependent packages manually:

```python
pip3 install textual-inputs
```

## Running the example

The example app was tested using Python 3.9 (it probabably works with 3.8 also).  To run the app:

```python
python3.9 sample_tui.py
```

## Structure

The extended Textual widgets, layouts, etc. are in the 'tui' subdirectory (yes, I know, these should be in a 'src' directory eventually).  


