import os
import importlib.machinery
import importlib.util
PluginFolder = os.path.join(os.path.dirname(os.path.realpath(__file__)),"..","plugins")
MainModule = "__init__"

def get_plugin(name, plugin_path):
    search_dirs = [PluginFolder, '.']
    if plugin_path:
        search_dirs = [plugin_path] + search_dirs
    for dir in search_dirs:
        location = os.path.join(dir, name)
        if not os.path.isdir(location) or not MainModule + ".py" in os.listdir(location):
            continue
        spec = importlib.machinery.PathFinder.find_spec(MainModule, [location])
        return {"name": name, "spec": spec, "path": location}
    raise Exception("Could not find plugin with name " + name)

def load_plugin(plugin):
    spec = plugin["spec"]
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
