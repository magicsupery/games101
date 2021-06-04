cmake_minimum_required(VERSION 3.10)
project(GAMES101)


set(CMAKE_CXX_STANDARD 17)

set(LIBRARY_OUTPUT_PATH ${PROJECT_BINARY_DIR}/lib)
set(EXECUTABLE_OUTPUT_PATH ${PROJECT_BINARY_DIR}/bin)

MACRO(SUBDIRLIST result curdir)
  FILE(GLOB children RELATIVE ${curdir} ${curdir}/*)
  message("children " ${children})
  SET(dirlist "")
  FOREACH(child ${children})
    IF(IS_DIRECTORY ${curdir}/${child})
		
	  get_filename_component(name ${child} NAME)
	  IF(name MATCHES "Assignment.*")
		LIST(APPEND dirlist ${child})
	  ENDIF()
    ENDIF()
  ENDFOREACH()
  SET(${result} ${dirlist})
ENDMACRO()


include_directories(${PROJECT_SOURCE_DIR})
include_directories(${PROJECT_SOURCE_DIR}/3rdparty/install/include)

#lib
link_directories(${PROJECT_SOURCE_DIR}/3rdparty/install/)
link_directories(${PROJECT_SOURCE_DIR}/3rdparty/install/lib)
link_directories(${PROJECT_SOURCE_DIR}/3rdparty/install/lib64)


set(OpenCV_DIR ${PROJECT_SOURCE_DIR}/3rdparty/install/)
find_package(OpenCV REQUIRED)
SUBDIRLIST(SUBDIRS ${PROJECT_SOURCE_DIR})
message("all dir " ${SUBDIRS})
LIST(APPEND CMAKE_PROGRAM_PATH ${OpenCV_LIB_PATH}/../bin/)
message("PATH ", ${CMAKE_PROGRAM_PATH})
FOREACH(subdir ${SUBDIRS})
  ADD_SUBDIRECTORY(${subdir}/src)
ENDFOREACH()