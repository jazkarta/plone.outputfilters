import re

from bs4 import BeautifulSoup
from plone.base.interfaces import IImagingSchema
from plone.outputfilters.interfaces import IFilter
from plone.registry.interfaces import IRegistry
from Products.CMFPlone.utils import safe_nativestring
from zope.component import getUtility
from zope.interface import implementer


@implementer(IFilter)
class ImageSrcsetFilter(object):
    """Converts img/figure tags with a data-srcset attribute into srcset definition.
    <picture>
        <source media="(max-width:768px) and (orientation:portrait)"
                srcset="resolveuid/44d84ffd32924bb8b9dbd720f43e761c/@@images/image/teaser" />
        <source media="(max-width:768px)"
                srcset="resolveuid/44d84ffd32924bb8b9dbd720f43e761c/@@images/image/large" />
        <source media="(min-width:992px)"
                srcset="resolveuid/44d84ffd32924bb8b9dbd720f43e761c/@@images/image/larger" />
        <source media="(min-width:1200px)"
                srcset="resolveuid/44d84ffd32924bb8b9dbd720f43e761c/@@images/image/great" />
        <source media="(min-width:1400px)"
                srcset="resolveuid/44d84ffd32924bb8b9dbd720f43e761c/@@images/image/huge" />
        <img src="resolveuid/44d84ffd32924bb8b9dbd720f43e761c/@@images/image/huge" />
    </picture>
    """

    order = 700

    def _shorttag_replace(self, match):
        tag = match.group(1)
        if tag in self.singleton_tags:
            return "<" + tag + " />"
        else:
            return "<" + tag + "></" + tag + ">"

    def is_enabled(self):
        if self.context is None:
            return False
        else:
            return True

    def __init__(self, context=None, request=None):
        self.current_status = None
        self.context = context
        self.request = request

    def __call__(self, data):
        data = re.sub(r"<([^<>\s]+?)\s*/>", self._shorttag_replace, data)
        soup = BeautifulSoup(safe_nativestring(data), "html.parser")
        self.image_srcsets = self.image_srcsets()

        for elem in soup.find_all("img"):
            srcset_name = elem.attrs.get("data-srcset", "")
            if not srcset_name:
                continue
            elem.replace_with(self.convert_to_srcset(srcset_name, elem, soup))
        return str(soup)

    def image_srcsets(self):
        registry = getUtility(IRegistry)
        settings = registry.forInterface(IImagingSchema, prefix="plone", check=False)
        return settings.image_srcsets

    def convert_to_srcset(self, srcset_name, elem, soup):
        """Converts the element to a srcset definition
        """
        srcset_config = self.image_srcsets.get(srcset_name)
        sourceset = srcset_config.get('sourceset')
        if not sourceset:
            return elem
        src = elem.attrs.get("src")
        picture_tag = soup.new_tag("picture")
        for i, source in enumerate(sourceset):
            scale = source['scale']
            media = source.get('media')
            title = elem.attrs.get('title')
            alt = elem.attrs.get('alt')
            klass = elem.attrs.get('class')
            if i == len(sourceset) - 1:
                source_tag = soup.new_tag("img", src=self.update_src_scale(src=src, scale=scale))
            else:
                # TODO guess type:
                source_tag = soup.new_tag("source", srcset=self.update_src_scale(src=src, scale=scale))
            source_tag["loading"] = "lazy"
            if media:
                source_tag["media"] = media
            if title:
                source_tag["title"] = title
            if alt:
                source_tag["alt"] = alt
            if klass:
                source_tag["class"] = klass
            picture_tag.append(source_tag)
        return picture_tag

    def update_src_scale(self, src, scale):
        parts = src.split("/")
        return "/".join(parts[:-1]) + "/{}".format(scale)