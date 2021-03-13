'''
 Mortal Kombat uncompressed GRA files viewer
 
 Copyright (c) 2021 ReWolf
 http://blog.rewolf.pl/
 
 This program is free software: you can redistribute it and/or modify
 it under the terms of the GNU Lesser General Public License as published
 by the Free Software Foundation, either version 3 of the License, or
 (at your option) any later version.
 
 This program is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU Lesser General Public License for more details.
 
 You should have received a copy of the GNU Lesser General Public License
 along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

from functools import cache
from typing import List
from PIL import Image
import itertools
import mktypes


def AddBorders(data: List[int], width: int, height: int, left: int, right: int,
               top: int, bottom: int, color: int) -> List[int]:
    ret = []
    for y in range(0, height):
        ret += [color] * left + data[y * width:y * width +
                                     width] + [color] * right
    if top != 0:
        ret = [color] * ((width + left + right) * top) + ret
    if bottom != 0:
        ret.extend([color] * ((width + left + right) * bottom))
    return ret


def AddClippingBox(sprite: mktypes.SpriteDescriptor,
                   clipping_box: mktypes.ClippingBox, color: int) -> List[int]:
    left_border = clipping_box.x_adjust - sprite.x
    right_border = clipping_box.width - sprite.width - left_border
    top_border = clipping_box.y_adjust - sprite.y
    bottom_border = clipping_box.height - sprite.height - top_border
    return AddBorders(sprite.data, sprite.width, sprite.height, left_border,
                      right_border, top_border, bottom_border, color)


MULT = 255.0 / 63


@cache
def Convert15to24bitRGB(v: int) -> mktypes.Color:
    r = int(round((((v >> 9) & 0x3F) | 1) * MULT))
    g = int(round((((v >> 4) & 0x3F) | 1) * MULT))
    b = int(round((((v << 1) & 0x3F) | 1) * MULT))
    return mktypes.Color(r, g, b)


def PreparePalette(input_pal: List[int]) -> List[mktypes.Color]:
    palette = [Convert15to24bitRGB(v) for v in input_pal]
    palette.extend([mktypes.Color(0xFF, 0xFF, 0xFF)] * (256 - len(input_pal)))
    return palette


def ApplyPalette(buffer: List[int], palette: List[mktypes.Color]) -> bytes:
    return bytes(
        itertools.chain.from_iterable([palette[c].tuple() for c in buffer]))


def CalculateClippingBox(
        sprites: List[mktypes.SpriteDescriptor]) -> mktypes.ClippingBox:
    min_x = min(sprites, key=lambda s: s.x).x
    min_y = min(sprites, key=lambda s: s.y).y
    max_x_w = max(sprites, key=lambda s: s.x + s.width)
    max_y_h = max(sprites, key=lambda s: s.y + s.height)
    width = max_x_w.x + max_x_w.width - min_x
    height = max_y_h.y + max_y_h.height - min_y
    x_adjust = max(sprites, key=lambda s: s.x).x
    y_adjust = max(sprites, key=lambda s: s.y).y
    return mktypes.ClippingBox(x_adjust, y_adjust, width, height)


def GetSpritesImage(sprites: List[mktypes.SpriteDescriptor],
                    palette: mktypes.Palette,
                    max_width: int = 1024) -> Image.Image:
    max_height = 0
    current_x = 0
    current_y = 0
    for sprite in sprites:
        if current_x + sprite.width > max_width:
            current_x = 0
            current_y += max_height
        current_x += sprite.width
        if sprite.height > max_height:
            max_height = sprite.height
    ret = Image.new("RGB", (
        max_width,
        current_y + max_height,
    ),
                    color=(255, 255, 255))
    max_height = 0
    current_x = 0
    current_y = 0
    for sprite in sprites:
        if current_x + sprite.width > max_width:
            current_x = 0
            current_y += max_height
        colored_sprite = ApplyPalette(sprite.data,
                                      PreparePalette(palette.colors))
        img = Image.frombuffer('RGB', (sprite.width, sprite.height),
                               colored_sprite, 'raw', 'RGB', 0, 1)
        ret.paste(img, box=(current_x, current_y))
        current_x += sprite.width
        if sprite.height > max_height:
            max_height = sprite.height
    return ret
