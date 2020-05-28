import pytest
from qtpy.QtWidgets import QDockWidget, QHBoxLayout, QPushButton, QVBoxLayout


def test_add_dock_widget(viewer_factory):
    """Test basic add_dock_widget functionality"""
    view, viewer = viewer_factory()
    widg = QPushButton('button')
    dwidg = viewer.window.add_dock_widget(widg, name='test')
    assert not dwidg.is_vertical
    assert viewer.window._qt_window.findChild(QDockWidget, 'test')
    assert dwidg.widget == widg
    dwidg._on_visibility_changed(True)  # smoke test

    widg2 = QPushButton('button')
    dwidg2 = viewer.window.add_dock_widget(widg2, name='test2', area='right')
    assert dwidg2.is_vertical
    assert viewer.window._qt_window.findChild(QDockWidget, 'test2')
    assert dwidg2.widget == widg2
    dwidg2._on_visibility_changed(True)  # smoke test

    with pytest.raises(ValueError):
        # 'under' is not a valid area
        viewer.window.add_dock_widget(widg2, name='test2', area='under')

    with pytest.raises(ValueError):
        # 'under' is not a valid area
        viewer.window.add_dock_widget(
            widg2, name='test2', allowed_areas=['under']
        )

    with pytest.raises(TypeError):
        # allowed_areas must be a list
        viewer.window.add_dock_widget(
            widg2, name='test2', allowed_areas='under'
        )


def test_add_dock_widget_from_list(viewer_factory):
    """Test that we can add a list of widgets and they will be combined"""
    view, viewer = viewer_factory()
    widg = QPushButton('button')
    widg2 = QPushButton('button')

    dwidg = viewer.window.add_dock_widget(
        [widg, widg2], name='test', area='right'
    )
    assert viewer.window._qt_window.findChild(QDockWidget, 'test')
    assert isinstance(dwidg.widget.layout, QVBoxLayout)

    dwidg = viewer.window.add_dock_widget(
        [widg, widg2], name='test2', area='bottom'
    )
    assert viewer.window._qt_window.findChild(QDockWidget, 'test2')
    assert isinstance(dwidg.widget.layout, QHBoxLayout)


def test_add_dock_widget_raises(viewer_factory):
    """Test that the widget passed must be a DockWidget."""
    view, viewer = viewer_factory()
    widg = object()

    with pytest.raises(TypeError):
        viewer.window.add_dock_widget(widg, name='test')
