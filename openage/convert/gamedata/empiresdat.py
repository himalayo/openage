# Copyright 2013-2019 the openage authors. See copying.md for legal info.

# TODO pylint: disable=C,R

import pickle
from zlib import decompress

from openage.convert.dataformat.version_detect import GameExpansion, GameEdition

from . import civ
from . import graphic
from . import maps
from . import playercolor
from . import research
from . import sound
from . import tech
from . import terrain
from . import unit
from ...log import spam, dbg, info, warn
from ..dataformat.genie_structure import GenieStructure
from ..dataformat.member_access import READ, READ_EXPORT, READ_UNKNOWN, SKIP
from ..dataformat.read_members import SubdataMember
from ..dataformat.value_members import MemberTypes as StorageType


# this file can parse and represent the empires2_x1_p1.dat file.
#
# the dat file contain all the information needed for running the game.
# all units, buildings, terrains, whatever are defined in this dat file.
#
# documentation for this can be found in `doc/gamedata`
# the binary structure, which the dat file has, is in `doc/gamedata.struct`
class EmpiresDat(GenieStructure):
    """
    class for fighting and beating the compressed empires2*.dat

    represents the main game data file.
    """

    name_struct_file   = "gamedata"
    name_struct        = "empiresdat"
    struct_description = "empires2_x1_p1.dat structure"

    @classmethod
    def get_data_format_members(cls, game_version):
        """
        Return the members in this struct.
        """
        data_format = [(READ, "versionstr", StorageType.STRING_MEMBER, "char[8]")]

        if game_version[0] is GameEdition.SWGB:
            data_format.extend([
                (READ, "civ_count_swgb", StorageType.INT_MEMBER, "uint16_t"),
                (READ_UNKNOWN, None, StorageType.INT_MEMBER, "int32_t"),
                (READ_UNKNOWN, None, StorageType.INT_MEMBER, "int32_t"),
                (READ_UNKNOWN, None, StorageType.INT_MEMBER, "int32_t"),
                (READ_UNKNOWN, None, StorageType.INT_MEMBER, "int32_t"),
            ])

        # terrain header data
        data_format.extend([
            (READ, "terrain_restriction_count", StorageType.INT_MEMBER, "uint16_t"),
            (READ, "terrain_count", StorageType.INT_MEMBER, "uint16_t"),   # number of "used" terrains
            (READ, "float_ptr_terrain_tables", StorageType.ARRAY_ID, "int32_t[terrain_restriction_count]"),
        ])

        if game_version[0] not in (GameEdition.ROR, GameEdition.AOE1DE):
            data_format.append((READ, "terrain_pass_graphics_ptrs", StorageType.ARRAY_ID, "int32_t[terrain_restriction_count]"))

        data_format.extend([
            (READ, "terrain_restrictions", StorageType.ARRAY_CONTAINER, SubdataMember(
                ref_type=terrain.TerrainRestriction,
                length="terrain_restriction_count",
                passed_args={"terrain_count"},
            )),

            # player color data
            (READ, "player_color_count", StorageType.INT_MEMBER, "uint16_t"),
            (READ, "player_colors", StorageType.ARRAY_CONTAINER, SubdataMember(
                ref_type=playercolor.PlayerColor,
                length="player_color_count",
            )),

            # sound data
            (READ_EXPORT, "sound_count", StorageType.INT_MEMBER, "uint16_t"),
            (READ_EXPORT, "sounds", StorageType.ARRAY_CONTAINER, SubdataMember(
                ref_type=sound.Sound,
                length="sound_count",
            )),

            # graphic data
            (READ, "graphic_count", StorageType.INT_MEMBER, "uint16_t"),
            (READ, "graphic_ptrs", StorageType.ARRAY_ID, "uint32_t[graphic_count]"),
            (READ_EXPORT, "graphics", StorageType.ARRAY_CONTAINER, SubdataMember(
                ref_type  = graphic.Graphic,
                length    = "graphic_count",
                offset_to = ("graphic_ptrs", lambda o: o > 0),
            )),

            # terrain data
            (SKIP, "virt_function_ptr", StorageType.ID_MEMBER, "int32_t"),
            (SKIP, "map_pointer", StorageType.ID_MEMBER, "int32_t"),
            (SKIP, "map_width", StorageType.INT_MEMBER, "int32_t"),
            (SKIP, "map_height", StorageType.INT_MEMBER, "int32_t"),
            (SKIP, "world_width", StorageType.INT_MEMBER, "int32_t"),
            (SKIP, "world_height", StorageType.INT_MEMBER, "int32_t"),
            (READ_EXPORT,  "tile_sizes", StorageType.ARRAY_CONTAINER, SubdataMember(
                ref_type=terrain.TileSize,
                length=19,      # number of tile types
            )),
            (SKIP, "padding1", StorageType.INT_MEMBER, "int16_t"),
        ])

        # Stored terrain number is hardcoded.
        # Usually less terrains are used by the game
        if game_version[0] is GameEdition.SWGB:
            data_format.append((READ_EXPORT, "terrains", StorageType.ARRAY_CONTAINER, SubdataMember(
                ref_type=terrain.Terrain,
                length=55,
            )))
        elif game_version[0] is GameEdition.AOE2DE:
            data_format.append((READ_EXPORT, "terrains", StorageType.ARRAY_CONTAINER, SubdataMember(
                ref_type=terrain.Terrain,
                length=200,
            )))
        elif game_version[0] is GameEdition.AOE1DE:
            data_format.append((READ_EXPORT, "terrains", StorageType.ARRAY_CONTAINER, SubdataMember(
                ref_type=terrain.Terrain,
                length=96,
            )))
        elif game_version[0] is GameEdition.HDEDITION:
            data_format.append((READ_EXPORT, "terrains", StorageType.ARRAY_CONTAINER, SubdataMember(
                ref_type=terrain.Terrain,
                length=100,
            )))
        elif game_version[0] is GameEdition.AOC:
            data_format.append((READ_EXPORT, "terrains", StorageType.ARRAY_CONTAINER, SubdataMember(
                ref_type=terrain.Terrain,
                length=42,
            )))
        else:
            data_format.append((READ_EXPORT, "terrains", StorageType.ARRAY_CONTAINER, SubdataMember(
                ref_type=terrain.Terrain,
                length=32,
            )))

        if game_version[0] is not GameEdition.AOE2DE:
            data_format.extend([
                (READ, "terrain_border", StorageType.ARRAY_CONTAINER, SubdataMember(
                    ref_type=terrain.TerrainBorder,
                    length=16,
                )),
                (SKIP, "map_row_offset", StorageType.INT_MEMBER, "int32_t"),
            ])

        if game_version[0] not in (GameEdition.ROR, GameEdition.AOE1DE):
            data_format.extend([
                (SKIP, "map_min_x", StorageType.FLOAT_MEMBER, "float"),
                (SKIP, "map_min_y", StorageType.FLOAT_MEMBER, "float"),
                (SKIP, "map_max_x", StorageType.FLOAT_MEMBER, "float"),
                (SKIP, "map_max_y", StorageType.FLOAT_MEMBER, "float"),
                (SKIP, "map_max_xplus1", StorageType.FLOAT_MEMBER, "float"),
                (SKIP, "map_min_yplus1", StorageType.FLOAT_MEMBER, "float"),
            ])

        data_format.extend([
            (READ, "terrain_count_additional", StorageType.INT_MEMBER, "uint16_t"),
            (READ, "borders_used", StorageType.INT_MEMBER, "uint16_t"),
            (READ, "max_terrain", StorageType.INT_MEMBER, "int16_t"),
            (READ_EXPORT, "tile_width", StorageType.INT_MEMBER, "int16_t"),
            (READ_EXPORT, "tile_height", StorageType.INT_MEMBER, "int16_t"),
            (READ_EXPORT, "tile_half_height", StorageType.INT_MEMBER, "int16_t"),
            (READ_EXPORT, "tile_half_width", StorageType.INT_MEMBER, "int16_t"),
            (READ_EXPORT, "elev_height", StorageType.INT_MEMBER, "int16_t"),
            (SKIP, "current_row", StorageType.INT_MEMBER, "int16_t"),
            (SKIP, "current_column", StorageType.INT_MEMBER, "int16_t"),
            (SKIP, "block_beginn_row", StorageType.INT_MEMBER, "int16_t"),
            (SKIP, "block_end_row", StorageType.INT_MEMBER, "int16_t"),
            (SKIP, "block_begin_column", StorageType.INT_MEMBER, "int16_t"),
            (SKIP, "block_end_column", StorageType.INT_MEMBER, "int16_t"),
        ])

        if game_version[0] not in (GameEdition.ROR, GameEdition.AOE1DE):
            data_format.extend([
                (SKIP, "search_map_ptr", StorageType.INT_MEMBER, "int32_t"),
                (SKIP, "search_map_rows_ptr", StorageType.INT_MEMBER, "int32_t"),
                (SKIP, "any_frame_change", StorageType.INT_MEMBER, "int8_t"),
            ])
        else:
            data_format.extend([
                (SKIP, "any_frame_change", StorageType.INT_MEMBER, "int32_t"),
                (SKIP, "search_map_ptr", StorageType.INT_MEMBER, "int32_t"),
                (SKIP, "search_map_rows_ptr", StorageType.INT_MEMBER, "int32_t"),
            ])

        data_format.extend([
            (SKIP, "map_visible_flag", StorageType.INT_MEMBER, "int8_t"),
            (SKIP, "fog_flag", StorageType.INT_MEMBER, "int8_t"),
        ])

        if game_version[0] is not GameEdition.AOE2DE:
            if game_version[0] is GameEdition.SWGB:
                data_format.extend([
                    (READ_UNKNOWN, "terrain_blob0", StorageType.ARRAY_INT, "uint8_t[25]"),
                    (READ_UNKNOWN, "terrain_blob1", StorageType.ARRAY_INT, "uint32_t[157]"),
                ])
            elif game_version[0] in (GameEdition.ROR, GameEdition.AOE1DE):
                data_format.extend([
                    (READ_UNKNOWN, "terrain_blob0", StorageType.ARRAY_INT, "uint8_t[2]"),
                    (READ_UNKNOWN, "terrain_blob1", StorageType.ARRAY_INT, "uint32_t[5]"),
                ])
            else:
                data_format.extend([
                    (READ_UNKNOWN, "terrain_blob0", StorageType.ARRAY_INT, "uint8_t[21]"),
                    (READ_UNKNOWN, "terrain_blob1", StorageType.ARRAY_INT, "uint32_t[157]"),
                ])

        data_format.extend([
            # random map config
            (READ, "random_map_count", StorageType.INT_MEMBER, "uint32_t"),
            (READ, "random_map_ptr", StorageType.ID_MEMBER, "uint32_t"),
            (READ, "map_infos", StorageType.ARRAY_CONTAINER, SubdataMember(
                ref_type=maps.MapInfo,
                length="random_map_count",
            )),
            (READ, "maps", StorageType.ARRAY_CONTAINER, SubdataMember(
                ref_type=maps.Map,
                length="random_map_count",
            )),

            # technology effect data
            (READ_EXPORT, "effect_bundle_count", StorageType.INT_MEMBER, "uint32_t"),
            (READ_EXPORT, "effect_bundles", StorageType.ARRAY_CONTAINER, SubdataMember(
                ref_type=tech.EffectBundle,
                length="effect_bundle_count",
            )),
        ])

        if game_version[0] is GameEdition.SWGB:
            data_format.extend([
                (READ, "unit_line_count", StorageType.INT_MEMBER, "uint16_t"),
                (READ, "unit_lines", StorageType.ARRAY_CONTAINER, SubdataMember(
                    ref_type=unit.UnitLine,
                    length="unit_line_count",
                )),
            ])

        # unit header data
        if game_version[0] not in (GameEdition.ROR, GameEdition.AOE1DE):
            data_format.extend([
                (READ_EXPORT, "unit_count", StorageType.INT_MEMBER, "uint32_t"),
                (READ_EXPORT, "unit_headers", StorageType.ARRAY_CONTAINER, SubdataMember(
                    ref_type=unit.UnitHeader,
                    length="unit_count",
                )),
            ])

        # civilisation data
        data_format.extend([
            (READ_EXPORT, "civ_count", StorageType.INT_MEMBER, "uint16_t"),
            (READ_EXPORT, "civs", StorageType.ARRAY_CONTAINER, SubdataMember(
                ref_type=civ.Civ,
                length="civ_count"
            )),
        ])

        if game_version[0] is GameEdition.SWGB:
            data_format.append((READ_UNKNOWN, None, StorageType.INT_MEMBER, "int8_t"))

        # research data
        data_format.extend([
            (READ_EXPORT, "research_count", StorageType.INT_MEMBER, "uint16_t"),
            (READ_EXPORT, "researches", StorageType.ARRAY_CONTAINER, SubdataMember(
                ref_type=research.Tech,
                length="research_count"
            )),
        ])

        if game_version[0] is GameEdition.SWGB:
            data_format.append((READ_UNKNOWN, None, StorageType.INT_MEMBER, "int8_t"))

        if game_version[0] not in (GameEdition.ROR, GameEdition.AOE1DE):
            data_format.extend([
                (SKIP, "time_slice", StorageType.INT_MEMBER, "int32_t"),
                (SKIP, "unit_kill_rate", StorageType.INT_MEMBER, "int32_t"),
                (SKIP, "unit_kill_total", StorageType.INT_MEMBER, "int32_t"),
                (SKIP, "unit_hitpoint_rate", StorageType.INT_MEMBER, "int32_t"),
                (SKIP, "unit_hitpoint_total", StorageType.INT_MEMBER, "int32_t"),
                (SKIP, "razing_kill_rate", StorageType.INT_MEMBER, "int32_t"),
                (SKIP, "razing_kill_total", StorageType.INT_MEMBER, "int32_t"),
            ])

            # technology tree data
            data_format.extend([
                (READ_EXPORT, "age_connection_count", StorageType.INT_MEMBER, "uint8_t"),
                (READ_EXPORT, "building_connection_count", StorageType.INT_MEMBER, "uint8_t"),
            ])

            if game_version[0] is GameEdition.SWGB:
                data_format.append((READ_EXPORT, "unit_connection_count", StorageType.INT_MEMBER, "uint16_t"))

            else:
                data_format.append((READ_EXPORT, "unit_connection_count", StorageType.INT_MEMBER, "uint8_t"))

            data_format.extend([
                (READ_EXPORT, "tech_connection_count", StorageType.INT_MEMBER, "uint8_t"),
                (READ_EXPORT, "total_unit_tech_groups", StorageType.INT_MEMBER, "int32_t"),
                (READ_EXPORT, "age_connections", StorageType.ARRAY_CONTAINER, SubdataMember(
                    ref_type=tech.AgeTechTree,
                    length="age_connection_count"
                )),
                (READ_EXPORT, "building_connections", StorageType.ARRAY_CONTAINER, SubdataMember(
                    ref_type=tech.BuildingConnection,
                    length="building_connection_count"
                )),
                (READ_EXPORT, "unit_connections", StorageType.ARRAY_CONTAINER, SubdataMember(
                    ref_type=tech.UnitConnection,
                    length="unit_connection_count"
                )),
                (READ_EXPORT, "tech_connections", StorageType.ARRAY_CONTAINER, SubdataMember(
                    ref_type=tech.ResearchConnection,
                    length="tech_connection_count"
                )),
            ])

        return data_format

    @classmethod
    def get_hash(cls):
        """
        Return the unique hash for the data format tree.
        """
        return cls.format_hash().hexdigest()


class EmpiresDatWrapper(GenieStructure):
    """
    This wrapper exists because the top-level element is discarded:
    The gathered data fields are passed to the parent,
    and are accumulated there to be processed further.

    This class acts as the parent for the "real" data values,
    and has no parent itself. Thereby this class is discarded
    and the child classes use this as parent for their return values.
    """

    name_struct_file   = "gamedata"
    name_struct        = "gamedata"
    struct_description = "wrapper for empires2_x1_p1.dat structure"

    @classmethod
    def get_data_format_members(cls, game_version):
        """
        Return the members in this struct.
        """
        data_format = [
            (READ_EXPORT, "empiresdat", StorageType.ARRAY_CONTAINER, SubdataMember(
                ref_type=EmpiresDat,
                length=1,
            )),
        ]

        return data_format


def load_gamespec(fileobj, game_version, cachefile_name=None, load_cache=False):
    """
    Helper method that loads the contents of a 'empires.dat' gzipped wrapper
    file.

    If cachefile_name is given, this file is consulted before performing the
    load.
    """
    # try to use the cached result from a previous run
    if cachefile_name and load_cache:
        try:
            with open(cachefile_name, "rb") as cachefile:
                # pickle.load() can fail in many ways, we need to catch all.
                # pylint: disable=broad-except
                try:
                    wrapper = pickle.load(cachefile)
                    info("using cached wrapper: %s", cachefile_name)
                    return wrapper
                except Exception:
                    warn("could not use cached wrapper:")
                    import traceback
                    traceback.print_exc()
                    warn("we will just skip the cache, no worries.")

        except FileNotFoundError:
            pass

    # read the file ourselves

    dbg("reading dat file")
    compressed_data = fileobj.read()
    fileobj.close()

    dbg("decompressing dat file")
    # -15: there's no header, window size is 15.
    file_data = decompress(compressed_data, -15)
    del compressed_data

    spam("length of decompressed data: %d", len(file_data))

    wrapper = EmpiresDatWrapper()
    _, gamespec = wrapper.read(file_data, 0, game_version)

    # Remove the list sorrounding the converted data
    gamespec = gamespec[0]

    if cachefile_name:
        dbg("dumping dat file contents to cache file: %s", cachefile_name)
        with open(cachefile_name, "wb") as cachefile:
            pickle.dump(gamespec, cachefile)

    return gamespec
