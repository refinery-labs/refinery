

def split_library_version_string(library):
    # Just a normal library install -- grab the latest
    if "@" not in str(library):
        return library, "latest"

    # If the library name is just an @ symbol
    if len(str(library)) == 1:
        return library, "latest"

    # Split the library based on the @ symbol into 2 halves. Note: The 1 means that it'll be split once only.
    library_version_tuple = str(library).split('@', 1)
    name = library_version_tuple[0]
    version = library_version_tuple[1]

    # Some libraries start with an @ symbol in the Node ecosystem
    # Like: @babel/node
    if len(name) == 0:
        # Just in case there is a version specified for a Node ecosystem package
        # @babel/node@1.0.0
        second_name, second_version = split_library_version_string(version)

        # If there wasn't an @ symbol in the second part, then the library string can be returned as-is
        if version == second_version:
            return library, "latest"

        return '@' + second_name, second_version

    return name, version


def generate_libraries_dict(libraries_list):

    # TODO just accept a dict/object in of an
    # array followed by converting it to one.
    libraries_dict = {}
    for library in libraries_list:
        library_name, library_version = split_library_version_string(library)

        libraries_dict[library_name] = library_version
    print(repr(libraries_dict))

    return libraries_dict
