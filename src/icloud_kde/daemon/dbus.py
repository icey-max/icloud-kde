"""D-Bus contract constants for the iCloud Drive daemon."""

from __future__ import annotations

BUS_NAME = "org.kde.ICloudDrive"
OBJECT_PATH = "/org/kde/ICloudDrive"
INTERFACE_NAME = "org.kde.ICloudDrive"

INTROSPECTION_XML = f"""\
<node>
  <interface name="{INTERFACE_NAME}">
    <method name="GetStatus">
      <arg name="status" type="a{{sv}}" direction="out"/>
    </method>
    <method name="GetItemState">
      <arg name="path" type="s" direction="in"/>
      <arg name="state" type="a{{sv}}" direction="out"/>
    </method>
    <method name="ListProblemItems">
      <arg name="problems" type="aa{{sv}}" direction="out"/>
    </method>
    <method name="Pause">
      <arg name="status" type="a{{sv}}" direction="out"/>
    </method>
    <method name="Resume">
      <arg name="status" type="a{{sv}}" direction="out"/>
    </method>
    <method name="RequestSync">
      <arg name="status" type="a{{sv}}" direction="out"/>
    </method>
    <method name="Hydrate">
      <arg name="path" type="s" direction="in"/>
      <arg name="state" type="a{{sv}}" direction="out"/>
    </method>
    <method name="GetConfig">
      <arg name="config" type="a{{sv}}" direction="out"/>
    </method>
    <method name="SetSyncRoot">
      <arg name="path" type="s" direction="in"/>
      <arg name="config" type="a{{sv}}" direction="out"/>
    </method>
    <signal name="StatusChanged">
      <arg name="status" type="a{{sv}}"/>
    </signal>
    <signal name="ItemStateChanged">
      <arg name="path" type="s"/>
      <arg name="state" type="a{{sv}}"/>
    </signal>
    <signal name="ProgressChanged">
      <arg name="progress" type="a{{sv}}"/>
    </signal>
    <signal name="ProblemRaised">
      <arg name="problem" type="a{{sv}}"/>
    </signal>
  </interface>
</node>
"""


def get_introspection_xml() -> str:
    """Return the daemon D-Bus introspection XML."""

    return INTROSPECTION_XML
