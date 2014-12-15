import sys
from libs.node import Node
from libs.timeserietable import TimeSerieTable


class NanoCube(object):
    def __init__(self, name, dimensions, loc_granularity=10, bin_size=3600):
        super(NanoCube, self).__init__()
        self.name = name
        self.world = Node()
        self.location_granularity = loc_granularity
        self.bin_size = bin_size

        # Init dimensions
        self.dimensions = dimensions
        self.dim_mapping = dict()
        for dim in dimensions:
            self.dim_mapping[dim] = dict()

    def add(self, entry):
        updated_nodes = []
        self._add_node(self.world, entry, 1, updated_nodes)

    def get_dimension(self):
        return len(self.dimensions) + 1

    def _add_node(self, root, entry, level, updated_nodes):
        child = None
        keys = self._keys_at_level(entry, level)
        stack = self._trail_proper_path(root, keys)
        while len(stack) > 0:
            n = stack.pop()
            update = False

            if n.has_a_single_child:
                n.set_shared_content(child.content)
            elif n.content is None:
                dim = self.get_dimension()
                if level == dim:
                    n.set_proper_content(TimeSerieTable())
                else:
                    n.set_proper_content(Node())
                update = True
            elif n.has_shared_content and n.content not in updated_nodes:
                content = n.content.copy()
                n.set_proper_content(content)
                update = True
            elif n.has_proper_content:
                update = True

            if update:
                if level == self.get_dimension():
                    n.content.insert(entry['Time'])
                else:
                    self._add_node(n.content, entry, level + 1, updated_nodes)
                updated_nodes.append(n.content)
            child = n

    def _trail_proper_path(self, root, keys):
        stack = []
        n = root
        stack.append(root)
        for key in keys:
            child = n.get_child(key)
            if child is None:
                child = Node()
                n.add_proper_child(key, child)
            elif Node.is_shared_child(n, child):
                child = child.copy()
                n.add_proper_child(key, child)
            stack.append(child)
            n = child
        return stack

    def _keys_at_level(self, entry, level):
        if level == 1:
            return self._get_location_keys(entry, self.location_granularity)
        else:
            return self._get_category_keys(entry, level)

    def _get_location_keys(self, entry, level):
        keys = []
        lat_bounds = {
            'max': 85,
            'min': -85
        }
        long_bounds = {
            'max': 180,
            'min': -180
        }

        for i in range(level):
            prev = "," if i == 0 else keys[i - 1]
            prev_long = prev.split(",")[0]
            prev_lat = prev.split(",")[1]

            lat_mean = (lat_bounds['max'] + lat_bounds['min']) / 2
            if entry['Latitude'] > lat_mean:
                lat_bounds['min'] = lat_mean
                prev_lat += "1"
            else:
                lat_bounds['max'] = lat_mean
                prev_lat += "0"

            long_mean = (long_bounds['max'] + long_bounds['min']) / 2
            if entry['Longitude'] > long_mean:
                long_bounds['min'] = long_mean
                prev_long += "1"
            else:
                long_bounds['max'] = long_mean
                prev_long += "0"

            keys.append(prev_long + "," + prev_lat)

        return keys

    def _get_category_keys(self, entry, level):
        selected_level = level - 2
        if selected_level >= len(self.dimensions):
            return []

        dim_name = self.dimensions[selected_level]
        mapping = self.dim_mapping[dim_name]

        if mapping.get(entry.get(dim_name)) is None:
            new_key = str(len(mapping))
            mapping[entry.get(dim_name)] = new_key
            return [new_key]
        else:
            return [mapping.get(entry.get(dim_name))]


    def _shallow_copy(node):
        return node.copy()

    def schema(self):
        ret = dict()
        dimensions = []
        location_dim = {
            'name': 'Location',
            'type': 'quad_tree_' + str(self.location_granularity),
            'values': {}
        }
        dimensions.append(location_dim)
        for index, dim_name in enumerate(self.dimensions):
            dim = {
                'name': dim_name,
                'type': 'cat_' + str(index + 1),
                'values': self.dim_mapping[dim_name]
            }
            dimensions.append(dim)
        ret['dimensions'] = dimensions
        return ret

    def __sizeof__(self):
        size = sys.getsizeof(self.dim_mapping) + sys.getsizeof(self.dimensions)
        size += sys.getsizeof(self.location_granularity)
        size += sys.getsizeof(self.world)
        return size
