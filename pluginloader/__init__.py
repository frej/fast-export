import os
import imp
PluginFolder = os.path.join(os.path.dirname(os.path.realpath(__file__)),"..","plugins")
MainModule = "__init__"

def get_plugin(name, plugin_path):
    search_dirs = [PluginFolder]
    if plugin_path:
        search_dirs = [plugin_path] + search_dirs
    for dir in search_dirs:
        location = os.path.join(dir, name)
        if not os.path.isdir(location) or not MainModule + ".py" in os.listdir(location):
            continue
        info = imp.find_module(MainModule, [location])
        return {"name": name, "info": info, "path": location}
    raise Exception("Could not find plugin with name " + name)

def load_plugin(plugin):
    return imp.load_module(MainModule, *plugin["info"])
