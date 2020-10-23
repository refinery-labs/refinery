'use strict';
var __assign =
  (this && this.__assign) ||
  function() {
    __assign =
      Object.assign ||
      function(t) {
        for (var s, i = 1, n = arguments.length; i < n; i++) {
          s = arguments[i];
          for (var p in s) if (Object.prototype.hasOwnProperty.call(s, p)) t[p] = s[p];
        }
        return t;
      };
    return __assign.apply(this, arguments);
  };
var __awaiter =
  (this && this.__awaiter) ||
  function(thisArg, _arguments, P, generator) {
    function adopt(value) {
      return value instanceof P
        ? value
        : new P(function(resolve) {
            resolve(value);
          });
    }
    return new (P || (P = Promise))(function(resolve, reject) {
      function fulfilled(value) {
        try {
          step(generator.next(value));
        } catch (e) {
          reject(e);
        }
      }
      function rejected(value) {
        try {
          step(generator['throw'](value));
        } catch (e) {
          reject(e);
        }
      }
      function step(result) {
        result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected);
      }
      step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
  };
var __generator =
  (this && this.__generator) ||
  function(thisArg, body) {
    var _ = {
        label: 0,
        sent: function() {
          if (t[0] & 1) throw t[1];
          return t[1];
        },
        trys: [],
        ops: []
      },
      f,
      y,
      t,
      g;
    return (
      (g = { next: verb(0), throw: verb(1), return: verb(2) }),
      typeof Symbol === 'function' &&
        (g[Symbol.iterator] = function() {
          return this;
        }),
      g
    );
    function verb(n) {
      return function(v) {
        return step([n, v]);
      };
    }
    function step(op) {
      if (f) throw new TypeError('Generator is already executing.');
      while (_)
        try {
          if (
            ((f = 1),
            y &&
              (t = op[0] & 2 ? y['return'] : op[0] ? y['throw'] || ((t = y['return']) && t.call(y), 0) : y.next) &&
              !(t = t.call(y, op[1])).done)
          )
            return t;
          if (((y = 0), t)) op = [op[0] & 2, t.value];
          switch (op[0]) {
            case 0:
            case 1:
              t = op;
              break;
            case 4:
              _.label++;
              return { value: op[1], done: false };
            case 5:
              _.label++;
              y = op[1];
              op = [0];
              continue;
            case 7:
              op = _.ops.pop();
              _.trys.pop();
              continue;
            default:
              if (!((t = _.trys), (t = t.length > 0 && t[t.length - 1])) && (op[0] === 6 || op[0] === 2)) {
                _ = 0;
                continue;
              }
              if (op[0] === 3 && (!t || (op[1] > t[0] && op[1] < t[3]))) {
                _.label = op[1];
                break;
              }
              if (op[0] === 6 && _.label < t[1]) {
                _.label = t[1];
                t = op;
                break;
              }
              if (t && _.label < t[2]) {
                _.label = t[2];
                _.ops.push(op);
                break;
              }
              if (t[2]) _.ops.pop();
              _.trys.pop();
              continue;
          }
          op = body.call(thisArg, _);
        } catch (e) {
          op = [6, e];
          y = 0;
        } finally {
          f = t = 0;
        }
      if (op[0] & 5) throw op[1];
      return { value: op[0] ? op[1] : void 0, done: true };
    }
  };
var __spreadArrays =
  (this && this.__spreadArrays) ||
  function() {
    for (var s = 0, i = 0, il = arguments.length; i < il; i++) s += arguments[i].length;
    for (var r = Array(s), k = 0, i = 0; i < il; i++)
      for (var a = arguments[i], j = 0, jl = a.length; j < jl; j++, k++) r[k] = a[j];
    return r;
  };
exports.__esModule = true;
exports.loadProjectFromDir = void 0;
var graph_1 = require('@/types/graph');
var path_1 = require('path');
var js_yaml_1 = require('js-yaml');
var v4_1 = require('uuid/v4');
var project_debug_utils_1 = require('@/utils/project-debug-utils');
var silly_names_1 = require('@/lib/silly-names');
var constants_1 = require('@/repo-compiler/shared/constants');
var git_utils_1 = require('@/repo-compiler/lib/git-utils');
function loadLambdaCode(fs, lambdaPath, blockConfig) {
  return __awaiter(this, void 0, void 0, function() {
    var repoContext, extension, blockCodeFilename, blockCodePath;
    return __generator(this, function(_a) {
      switch (_a.label) {
        case 0:
          if (!blockConfig.language) {
            repoContext = {
              filename: lambdaPath,
              fileContent: JSON.stringify(blockConfig)
            };
            throw new git_utils_1.RepoCompilationError('no language set in block', repoContext);
          }
          extension = project_debug_utils_1.languageToFileExtension[blockConfig.language];
          blockCodeFilename = constants_1.BLOCK_CODE_FILENAME + '.' + extension;
          blockCodePath = path_1['default'].join(lambdaPath, blockCodeFilename);
          return [4 /*yield*/, git_utils_1.readFile(fs, blockCodePath)];
        case 1:
          return [2 /*return*/, _a.sent()];
      }
    });
  });
}
function loadLambdaBlock(fs, lambdaPath) {
  return __awaiter(this, void 0, void 0, function() {
    var blockConfigPathExists, repoContext, blockConfig, _a, _b, _c;
    var _d;
    return __generator(this, function(_e) {
      switch (_e.label) {
        case 0:
          return [4 /*yield*/, git_utils_1.pathExists(fs, lambdaPath, constants_1.LAMBDA_CONFIG_FILENAME)];
        case 1:
          blockConfigPathExists = _e.sent();
          if (!blockConfigPathExists) {
            repoContext = {
              filename: path_1['default'].join(lambdaPath, constants_1.LAMBDA_CONFIG_FILENAME)
            };
            throw new git_utils_1.RepoCompilationError('Lambda block does not exist', repoContext);
          }
          _b = (_a = js_yaml_1['default']).safeLoad;
          return [4 /*yield*/, git_utils_1.readFile(fs, lambdaPath, constants_1.LAMBDA_CONFIG_FILENAME)];
        case 2:
          blockConfig = _b.apply(_a, [_e.sent()]);
          _c = [
            __assign(
              {
                // @ts-ignore
                // Just in case there is not an ID... Add it.
                id: v4_1['default']()
              },
              blockConfig
            )
          ];
          _d = {};
          return [4 /*yield*/, loadLambdaCode(fs, lambdaPath, blockConfig)];
        case 3:
          return [2 /*return*/, __assign.apply(void 0, _c.concat([((_d.code = _e.sent()), _d)]))];
      }
    });
  });
}
function getLambdaSharedFileLink(lambdaNode, sharedFileTargetRelativePath, sharedFileLinkPath, sharedFileLookup) {
  var lambdaSharedFilesPath = path_1['default'].dirname(sharedFileLinkPath);
  var sharedFilePath = path_1['default'].resolve(lambdaSharedFilesPath, sharedFileTargetRelativePath);
  var sharedFileConfig = sharedFileLookup[sharedFilePath];
  if (!sharedFileConfig) {
    var repoContext = {
      filename: sharedFilePath
    };
    throw new git_utils_1.RepoCompilationError('lambda shared file was not found in shared file folder', repoContext);
  }
  return {
    id: v4_1['default'](),
    node: lambdaNode,
    version: '1.0.0',
    file_id: sharedFileConfig.id,
    path: '',
    type: graph_1.WorkflowFileLinkType.SHARED_FILE_LINK
  };
}
function loadLambdaSharedBlocks(fs, lambdaPath, lambdaNode, sharedFileLookup) {
  return __awaiter(this, void 0, void 0, function() {
    var sharedFileLinksPath, e_1, sharedFileLinks;
    var _this = this;
    return __generator(this, function(_a) {
      switch (_a.label) {
        case 0:
          sharedFileLinksPath = path_1['default'].join(lambdaPath, constants_1.LAMBDA_SHARED_FILES_DIR);
          _a.label = 1;
        case 1:
          _a.trys.push([1, 3, , 4]);
          return [4 /*yield*/, fs.promises.stat(sharedFileLinksPath)];
        case 2:
          _a.sent();
          return [3 /*break*/, 4];
        case 3:
          e_1 = _a.sent();
          return [2 /*return*/, []];
        case 4:
          return [4 /*yield*/, fs.promises.readdir(sharedFileLinksPath)];
        case 5:
          sharedFileLinks = _a.sent();
          return [
            2 /*return*/,
            Promise.all(
              sharedFileLinks
                .map(function(sharedFileLink) {
                  return path_1['default'].join(sharedFileLinksPath, sharedFileLink);
                })
                .filter(function(sharedFileLinkPath) {
                  return __awaiter(_this, void 0, void 0, function() {
                    return __generator(this, function(_a) {
                      switch (_a.label) {
                        case 0:
                          return [4 /*yield*/, git_utils_1.isPathValidSymlink(fs, sharedFileLinkPath)];
                        case 1:
                          return [2 /*return*/, _a.sent()];
                      }
                    });
                  });
                })
                .map(function(sharedFileLinkPath) {
                  return __awaiter(_this, void 0, void 0, function() {
                    var sharedFileTargetRelativePath;
                    return __generator(this, function(_a) {
                      switch (_a.label) {
                        case 0:
                          return [4 /*yield*/, git_utils_1.readlink(fs, sharedFileLinkPath)];
                        case 1:
                          sharedFileTargetRelativePath = _a.sent();
                          return [
                            2 /*return*/,
                            getLambdaSharedFileLink(
                              lambdaNode,
                              sharedFileTargetRelativePath,
                              sharedFileLinkPath,
                              sharedFileLookup
                            )
                          ];
                      }
                    });
                  });
                })
            )
          ];
      }
    });
  });
}
function loadLambdaBlocks(fs, repoDir, sharedFileLookup) {
  return __awaiter(this, void 0, void 0, function() {
    var lambdaPath, e_2, lambdas;
    var _this = this;
    return __generator(this, function(_a) {
      switch (_a.label) {
        case 0:
          lambdaPath = path_1['default'].join(repoDir, constants_1.GLOBAL_BASE_PATH, constants_1.PROJECT_LAMBDA_DIR);
          _a.label = 1;
        case 1:
          _a.trys.push([1, 3, , 4]);
          return [4 /*yield*/, fs.promises.stat(lambdaPath)];
        case 2:
          _a.sent();
          return [3 /*break*/, 4];
        case 3:
          e_2 = _a.sent();
          console.error('Could not stat block: ' + lambdaPath);
          return [
            2 /*return*/,
            {
              sharedFileLinks: [],
              lambdaBlockConfigs: []
            }
          ];
        case 4:
          return [4 /*yield*/, fs.promises.readdir(lambdaPath)];
        case 5:
          lambdas = _a.sent();
          return [
            4 /*yield*/,
            lambdas
              .map(function(lambdaFilename) {
                return path_1['default'].join(lambdaPath, lambdaFilename);
              })
              .reduce(function(loadedConfigs, lambdaPath) {
                return __awaiter(_this, void 0, void 0, function() {
                  var resolvedLoadedConfigs, lambdaBlock, sharedFileLinks;
                  return __generator(this, function(_a) {
                    switch (_a.label) {
                      case 0:
                        return [4 /*yield*/, loadedConfigs];
                      case 1:
                        resolvedLoadedConfigs = _a.sent();
                        return [4 /*yield*/, loadLambdaBlock(fs, lambdaPath)];
                      case 2:
                        lambdaBlock = _a.sent();
                        return [4 /*yield*/, loadLambdaSharedBlocks(fs, lambdaPath, lambdaBlock.id, sharedFileLookup)];
                      case 3:
                        sharedFileLinks = _a.sent();
                        return [
                          2 /*return*/,
                          {
                            sharedFileLinks: __spreadArrays(resolvedLoadedConfigs.sharedFileLinks, sharedFileLinks),
                            lambdaBlockConfigs: __spreadArrays(resolvedLoadedConfigs.lambdaBlockConfigs, [lambdaBlock])
                          }
                        ];
                    }
                  });
                });
              }, Promise.resolve({ sharedFileLinks: [], lambdaBlockConfigs: [] }))
          ];
        case 6:
          return [2 /*return*/, _a.sent()];
      }
    });
  });
}
function loadSharedFileConfig(fs, sharedFilePath, sharedFileName) {
  return __awaiter(this, void 0, void 0, function() {
    var _a;
    return __generator(this, function(_b) {
      switch (_b.label) {
        case 0:
          _a = {
            id: v4_1['default'](),
            name: sharedFileName,
            version: '1.0.0'
          };
          return [4 /*yield*/, git_utils_1.readFile(fs, sharedFilePath)];
        case 1:
          return [2 /*return*/, ((_a.body = _b.sent()), (_a.type = graph_1.WorkflowFileType.SHARED_FILE), _a)];
      }
    });
  });
}
function loadSharedFiles(fs, repoDir) {
  return __awaiter(this, void 0, void 0, function() {
    var sharedFilesPath, e_3, sharedFiles;
    var _this = this;
    return __generator(this, function(_a) {
      switch (_a.label) {
        case 0:
          sharedFilesPath = path_1['default'].join(
            repoDir,
            constants_1.GLOBAL_BASE_PATH,
            constants_1.PROJECT_SHARED_FILES_DIR
          );
          _a.label = 1;
        case 1:
          _a.trys.push([1, 3, , 4]);
          return [4 /*yield*/, fs.promises.stat(sharedFilesPath)];
        case 2:
          _a.sent();
          return [3 /*break*/, 4];
        case 3:
          e_3 = _a.sent();
          console.error('Could not stat shared file folder: ' + sharedFilesPath);
          return [2 /*return*/, {}];
        case 4:
          return [4 /*yield*/, fs.promises.readdir(sharedFilesPath)];
        case 5:
          sharedFiles = _a.sent();
          return [
            4 /*yield*/,
            sharedFiles.reduce(function(lookup, sharedFileName) {
              return __awaiter(_this, void 0, void 0, function() {
                var resolvedLookup, sharedFilePath, _a, _b;
                var _c;
                return __generator(this, function(_d) {
                  switch (_d.label) {
                    case 0:
                      return [4 /*yield*/, lookup];
                    case 1:
                      resolvedLookup = _d.sent();
                      sharedFilePath = path_1['default'].join(sharedFilesPath, sharedFileName);
                      _a = [__assign({}, resolvedLookup)];
                      _c = {};
                      _b = sharedFilePath;
                      return [4 /*yield*/, loadSharedFileConfig(fs, sharedFilePath, sharedFileName)];
                    case 2:
                      return [2 /*return*/, __assign.apply(void 0, _a.concat([((_c[_b] = _d.sent()), _c)]))];
                  }
                });
              });
            }, Promise.resolve({}))
          ];
        case 6:
          return [2 /*return*/, _a.sent()];
      }
    });
  });
}
function loadProjectFromDir(fs, projectID, sessionID, repoDir) {
  return __awaiter(this, void 0, void 0, function() {
    var projectConfigFilename,
      projectConfigExists,
      repoContext,
      loadedProjectConfig,
      _a,
      _b,
      sharedFileLookup,
      sharedFileConfigs,
      loadedLambdaConfigs;
    return __generator(this, function(_c) {
      switch (_c.label) {
        case 0:
          projectConfigFilename = path_1['default'].join(
            constants_1.GLOBAL_BASE_PATH,
            '' + constants_1.PROJECTS_CONFIG_FOLDER + projectID + '.yaml'
          );
          return [4 /*yield*/, git_utils_1.pathExists(fs, repoDir, projectConfigFilename)];
        case 1:
          projectConfigExists = _c.sent();
          if (!projectConfigExists) {
            repoContext = {
              filename: projectConfigFilename
            };
            throw new git_utils_1.RepoCompilationError('Project config does not exist', repoContext);
          }
          _b = (_a = js_yaml_1['default']).safeLoad;
          return [4 /*yield*/, git_utils_1.readFile(fs, repoDir, projectConfigFilename)];
        case 2:
          loadedProjectConfig = _b.apply(_a, [_c.sent()]);
          return [4 /*yield*/, loadSharedFiles(fs, repoDir)];
        case 3:
          sharedFileLookup = _c.sent();
          sharedFileConfigs = Object.values(sharedFileLookup);
          return [4 /*yield*/, loadLambdaBlocks(fs, repoDir, sharedFileLookup)];
        case 4:
          loadedLambdaConfigs = _c.sent();
          return [
            2 /*return*/,
            __assign(
              __assign(
                {
                  // @ts-ignore
                  // default values
                  name: silly_names_1['default'](),
                  // @ts-ignore
                  version: 1,
                  // @ts-ignore
                  workflow_relationships: []
                },
                loadedProjectConfig
              ),
              {
                // Must happen after merging of the loaded Project config, otherwise can result in clobbering of UUIDs between projects
                project_id: projectID,
                // values tracked by file system
                workflow_states: __spreadArrays(
                  loadedProjectConfig.workflow_states,
                  loadedLambdaConfigs.lambdaBlockConfigs
                ),
                workflow_files: __spreadArrays(loadedProjectConfig.workflow_files, sharedFileConfigs),
                workflow_file_links: __spreadArrays(
                  loadedProjectConfig.workflow_file_links,
                  loadedLambdaConfigs.sharedFileLinks
                )
              }
            )
          ];
      }
    });
  });
}
exports.loadProjectFromDir = loadProjectFromDir;
