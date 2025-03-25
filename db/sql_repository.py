from abc import ABC, abstractmethod
from sqlmodel import SQLModel, select  # Session
from db.session import async_session
from typing import Union, Dict, List, Any
from sqlalchemy.engine.result import ScalarResult
from copy import deepcopy
from db.models import Events, Incidents
from core.logger import logger
from sqlalchemy.exc import IntegrityError


class AbstractRepository(ABC):
    @abstractmethod
    async def get_all(self):
        raise NotImplementedError(self.__class__.__name__ + ': not implemented')

    @abstractmethod
    async def get_explicit(self, item: SQLModel):
        raise NotImplementedError(self.__class__.__name__ + ': not implemented')

    @abstractmethod
    async def delete_all(self):
        raise NotImplementedError(self.__class__.__name__ + ': not implemented')

    @abstractmethod
    async def add_one(self, item):
        raise NotImplementedError(self.__class__.__name__ + ': not implemented')

    @abstractmethod
    async def get_one(self):
        raise NotImplementedError(self.__class__.__name__ + ': not implemented')


class SQLModelRepository(AbstractRepository):
    model = None
    model_unknown = None
    filter_by = dict()

    async def get_all(self):
        async with async_session() as session:
            async with session.begin():
                data = await session.query(self.model)  # ???  .exec()
                result = data.all()
                print('\n>>>>>>>>>>>>>>>>> run GET_ALL <<<<<<<<<<<<<<<<<<<<')
                return result

    async def delete_explicit(self, **filter_by) -> ScalarResult | None:
        # inc = {}
        async with async_session() as session:
            async with session.begin():
                # statement = select(self.model).where(self.model.hostname == item.hostname, self.model.interface == item.interface)
                statement = select(self.model).filter_by(**filter_by).limit(1)
                data = await session.execute(statement)
                if data:
                    # inc = data.model_dump()
                    item = data.one_or_none()
                    # event = Events.model_validate(item)
                    if item:
                        print(f'\n>>>>>>>>>>>>>>>>> {item[0]} <<<<<<<<<<<<<<<<<<<<')
                        # new_item = session.get(self.model, key)
                        # new_item = session.query(self.model).get(item.model_dump()['uuid'])
                        # print(f'\n>>>>>>>>>>>>>>>>> {new_item} <<<<<<<<<<<<<<<<<<<<')
                        # row_dict = row.model_dump()
                        # item = session.merge(self.model(**row_dict))
                        await session.delete(item[0])
                        await session.commit()
                print('\n>>>>>>>>>>>>>>>>> run DELETE_EXPLICIT <<<<<<<<<<<<<<<<<<<<')
        return data

    async def get_explicit(self, item: SQLModel) -> Dict[str, Any] | None:
        inc = {}
        async with async_session() as session:
            async with session.begin():
                # statement = select(self.model).where(self.model.hostname == item.hostname, self.model.interface == item.interface)
                statement = select(self.model).where(self.model.hostname == item.hostname).where(self.model.interface == item.interface).limit(1)
                data = await session.execute(statement)
                print(f'\n>>>>>>>>>>>>>>>>> run GET_EXPLICIT {data} <<<<<<<<<<<<<<<<<<<<')
                if data:
                    item = data.one_or_none()
                    if item:
                        inc = item[0].model_dump()
        return inc

    async def find_one(self, hostname: str, interface: str) -> Dict[str, Any] | None:
        inc = {}
        async with async_session() as session:
            async with session.begin():
                statement = select(self.model).where(self.model.hostname == hostname).where(self.model.interface == interface).limit(1)
                data = await session.execute(statement)
                print(f'\n>>>>>>>>>>>>>>>>> run FIND_ONE {type(data)} {data} <<<<<<<<<<<<<<<<<<<<')
                if data:
                    item = data.one_or_none()
                    if item:
                        inc = item[0].model_dump()
        return inc

    # async def find_one(self, hostname: str, interface: str) -> Dict[str, Any] | None:
    #     inc = {}
    #     with Session(engine) as session:
    #         with session.begin():
    #             statement = select(self.model).where(self.model.hostname == hostname).where(self.model.interface == interface).limit(1)
    #             data = session.execute(statement).one_or_none()
    #             print(f'\n>>>>>>>>>>>>>>>>> run FIND_ONE {type(data)} {data} <<<<<<<<<<<<<<<<<<<<')
    #             if data:
    #                 inc = data.model_dump()
    #     return inc

    async def get_one(self) -> ScalarResult | None:
        async with async_session() as session:
            async with session.begin():
                statement = select(self.model).where(self.model.stage == 'initial').where(self.model.permit == True).where(self.model.running == False).limit(1)
                data = await session.execute(statement)
                if data:
                    item = data.one_or_none()
                    if item:
                        result = deepcopy(item[0])
                    # make_transient(data)
                    print(f'\n>>>>>>>>>>>>>>>>> run GET_ONE {data} <<<<<<<<<<<<<<<<<<<<')
        return result

    async def get_one_as_dict_with_filter(self, model=None, **filter_by) -> Dict[str, Any] | None:
        inc = None
        if model:
            self.model = model
        async with async_session() as session:
            async with session.begin():
                statement = select(self.model).filter_by(**filter_by).limit(1)
                # .where(self.model.stage == 'initial').where(self.model.permit == True).where(self.model.running == False).limit(1)
                data = await session.execute(statement)
                if data:
                    item = data.one_or_none()
                    if item:
                        inc = item[0].model_dump()
                    # result = deepcopy(data)
                    # make_transient(data)
                    print(f'\n>>>>>>>>>>>>>>>>> run GET_ONE_AS_DICT_BY_FILTER {data} <<<<<<<<<<<<<<<<<<<<')
        return inc

    async def get_all_as_dict_with_filter(self, **filter_by) -> List[Dict[str, Any]] | None:
        incs = []
        async with async_session() as session:
            async with session.begin():
                statement = select(self.model).filter_by(**filter_by)
                # .where(self.model.stage == 'initial').where(self.model.permit == True).where(self.model.running == False).limit(1)
                data = await session.execute(statement)
                items = data.all()
                if items:
                    print(f'\n>>>>>>>>>>>>>>>>> run GET_ALL_AS_DICT_BY_FILTER {data} <<<<<<<<<<<<<<<<<<<<')
                    print(f'\n >>> items: {items}')
                    if len(items):
                        print(f'\n >>> item1: {items[0]}')
                    for item in items:
                        print(f'\n >>> item: {item}')
                        print(f'\n >>> type item: {type(item)}')
                        if item:
                            incs.append(item[0].model_dump())
                        # result = deepcopy(data)
                        # make_transient(data)
        return incs

    async def pop(self) -> ScalarResult | None:
        async with async_session() as session:
            async with session.begin():
                statement = select(self.model).with_for_update(read=True, nowait=True).limit(1)
                data = await session.execute(statement)
                if data:
                    await session.delete(data.first())
                    await session.commit()
                print('\n>>>>>>>>>>>>>>>>> run POP <<<<<<<<<<<<<<<<<<<<')
        return data

    async def update(self, inc: SQLModel) -> bool:
        print(">>> INC:", inc)
        print(">>> TYPE_INC:", type(inc))
        async with async_session() as session:
            async with session.begin():
                statement = select(self.model).with_for_update(read=True, nowait=True).where(self.model.uuid == inc.uuid).limit(1)
                inc_exists = await session.execute(statement)
                if inc_exists:
                    print(">>> inc_exists:", inc_exists)
                    item = inc_exists.one_or_none()
                    print(f">>> item: {type(item)} {item}")
                    inc_model = Incidents.sqlmodel_update(Incidents(), obj=inc)
                    await session.delete(item[0])
                    session.add(inc_model)
                    await session.commit()
                    print(f'\n>>>>>>>>>>>>>>>>> run INC_UPDATE <<<<<<<<<<<<<<<<<<<<')
                else:
                    session.add(inc)
                    await session.commit()
                    print(f'\n>>>>>>>>>>>>>>>>> run INC_INSERT <<<<<<<<<<<<<<<<<<<<')
        return True

    async def delete_all(self):
        async with async_session() as session:
            async with session.begin():
                await session.query(self.model).delete()
                await session.commit()

    async def add_one(self, item: SQLModel, filter_by: Union[Dict[str, str], Dict[str, List]] = None) -> SQLModel | None:
        """Adds an item to the database with optional filtering criteria.

        Args:
            item: The item (SQLModel instance) to be added to the database.
            filter_by: A dictionary containing filter criteria.
                       - For list values: keys represent fields, values are lists to match against (IN clause).
                       - For string values: keys represent fields, values are exact matches (= clause).
                       If None, defaults to self.filter_by (optional attribute).
        """

        # Use the provided filter_by or default to self.filter_by if available
        if filter_by is None:
            filter_by = getattr(self, 'filter_by', None)

        # Check if filter_by is a dictionary (if provided)
        if filter_by and not isinstance(filter_by, dict):
            raise TypeError("filter_by must be a dictionary or None")

        # Build the query logic based on the type of filter_by value for each key
        permit_by_filter = True
        if filter_by:
            for key, value in filter_by.items():
                # Check if value is a list (IN clause)
                if isinstance(value, list):
                    if getattr(item, key) not in value:
                        permit_by_filter = False
                        break
                # Otherwise, treat it as a string (exact match)
                else:
                    if getattr(item, key, None) != value:
                        permit_by_filter = False
                        break

        if permit_by_filter:
            async with async_session() as session:
                # print(f'\n>>>>>>>>>>>>>>>>> run ADD_ONE: {item} <<<<<<<<<<<<<<<<<<<<')
                try:
                    async with session.begin():
                        session.add(item)
                        await session.commit()
                except IntegrityError as e:
                    if isinstance(item, Events):
                        host_interface = item.model_dump(include={"hostname","interface"})
                        logger.error(f"Error adding item {host_interface} to database: {e}")
                    await session.rollback()
                    return None
            return item
        else:
            return None  # Indicate item was not added due to filter

    # @staticmethod
    # async def backup():
    #     with Session(engine) as session:
    #         with session.begin():
    #             session.executeute(text("TRUNCATE TABLE cmdbnetworkhostbackup; "
    #                                  "INSERT INTO cmdbnetworkhostbackup SELECT * FROM cmdbnetworkhost;"))
    #             session.commit()
