from sqlmodel import Field, SQLModel
from typing import Optional
from datetime import datetime
import uuid as uuid_pkg
from sqlalchemy.dialects import postgresql
from sqlalchemy import UniqueConstraint


# type: "InErrors"
# hostname: ""
# interface: ""
# description: ""
# value: 

host_role_type = postgresql.ENUM(
   "core",
   "aggregate",
   "boarder",
   "edge",
   "unspecified",
   name=f"host_role"
)


class CMDBNetworkHost(SQLModel, table=True):
    uuid: uuid_pkg.UUID = Field(default_factory=uuid_pkg.uuid4,
                                primary_key=True,
                                index=True,
                                nullable=False,
                                sa_column_kwargs={
                                    "unique": True
                                })
    HostName: str = Field(default=None, nullable=False, unique=True)
    NodeMember: int = Field(default=None, nullable=False)
    Status: str = Field(default=None, nullable=False)
    Interfaces: Optional[str] = Field(default=None, nullable=True)
    HardwareModelName: str = Field(default=None, nullable=False)
    NetworkType: Optional[str] = Field(default=None, nullable=True)
    NetworkRoles: Optional[str] = Field(default=None, nullable=True)
    OrgUnitName: str = Field(default=None, nullable=False)
    DataCenterLocation: str = Field(default=None, nullable=False)
    DataCenterLocationId: int = Field(default=None, nullable=False)


class CMDBNetworkHostBackup(SQLModel, table=True):
    uuid: uuid_pkg.UUID = Field(default_factory=uuid_pkg.uuid4,
                                primary_key=True,
                                index=True,
                                nullable=False,
                                sa_column_kwargs={
                                    "unique": True
                                })
    HostName: str = Field(default=None, nullable=False, unique=True)
    NodeMember: int = Field(default=None, nullable=False)
    Status: str = Field(default=None, nullable=False)
    Interfaces: Optional[str] = Field(default=None, nullable=True)
    HardwareModelName: str = Field(default=None, nullable=False)
    NetworkType: Optional[str] = Field(default=None, nullable=True)
    NetworkRoles: Optional[str] = Field(default=None, nullable=True)
    OrgUnitName: str = Field(default=None, nullable=False)
    DataCenterLocation: str = Field(default=None, nullable=False)
    DataCenterLocationId: int = Field(default=None, nullable=False)
    # DataCenterLocationName: str = Field(default=None, nullable=False)


class Events(SQLModel, table=True):
    uuid: uuid_pkg.UUID = Field(default_factory=uuid_pkg.uuid4,
                                primary_key=True,
                                index=True,
                                nullable=False,
                                sa_column_kwargs={
                                    "unique": True
                                })
    type: str = Field(default=None, nullable=False)
    hostname: str = Field(default=None, foreign_key="cmdbnetworkhostbackup.HostName", nullable=False)
    interface: str = Field(default=None, nullable=False)
    description: str = Field(default=None, nullable=False)
    link_type: Optional[str] = Field(default=None, nullable=True)
    peer: Optional[str] = Field(default=None, nullable=True)
    value: str = Field(default=None, nullable=False)
    created_at: datetime = Field(default_factory=datetime.now, nullable=False)


class EventsUnknown(SQLModel, table=True):
    uuid: uuid_pkg.UUID = Field(default_factory=uuid_pkg.uuid4,
                                primary_key=True,
                                index=True,
                                nullable=False,
                                sa_column_kwargs={
                                    "unique": True
                                })
    type: str = Field(default=None, nullable=False)
    hostname: str = Field(default=None, nullable=False)
    interface: str = Field(default=None, nullable=False)
    description: str = Field(default=None, nullable=False)
    link_type: Optional[str] = Field(default=None, nullable=True)
    peer: Optional[str] = Field(default=None, nullable=True)
    value: str = Field(default=None, nullable=False)
    created_at: datetime = Field(default_factory=datetime.now, nullable=False)


class Incidents(SQLModel, table=True):
    uuid: uuid_pkg.UUID = Field(default_factory=uuid_pkg.uuid4,
                                primary_key=True,
                                index=True,
                                nullable=False,
                                sa_column_kwargs={
                                    "unique": True
                                })
    event_id: uuid_pkg.UUID = Field(nullable=False,
                                    sa_column_kwargs={
                                        "unique": True
                                    })
    hostname: str = Field(default=None, nullable=False)
    interface: str = Field(default=None, nullable=False)
    link_type: str = Field(default=None, nullable=False)
    peer: str = Field(default=None, nullable=False)
    status_h: str = Field(default=None, nullable=False)
    status_p: str = Field(default=None, nullable=True)
    role_h: str = Field(default=None, nullable=False)
    role_p: str = Field(default=None, nullable=True)
    model_h: str = Field(default=None, nullable=False)
    model_p: str | None = Field(default=None, nullable=True)
    classname: str = Field(default=None, nullable=False)
    metric_type: str = Field(default=None, nullable=False)
    metric_value: str = Field(default=None, nullable=False)
    assigned_to: str = Field(default=None, nullable=False)
    created_at: datetime = Field(default_factory=datetime.now, nullable=False)
    params: Optional[bytes] = Field(default=None, nullable=True)
    priority: str = Field(default="Critical", nullable=False)
    stage: str = Field(default="initial", nullable=False)
    permit: bool = Field(default=True, nullable=False)
    running: bool = Field(default=False, nullable=False)  # stop/start
    

    __table_args__ = (
        UniqueConstraint("hostname", "interface", name="unique_hostname_interface"),
    )

    def __repr__(self):
        return f"{self.hostname} {self.interface} {self.link_type} {self.peer} {self.status_h} {self.status_p} {self.role_h} {self.role_p} {self.classname} {self.stage}"

    def __str__(self):
        return f"Hostname: {self.hostname}, Port: {self.interface}, Link_Type: {self.link_type}, Classname: {self.classname}, Stage: {self.stage}"
