cmake_minimum_required(VERSION 3.10)
project(Ass1)

find_package(OpenCV REQUIRED)

set(CMAKE_CXX_STANDARD 17)

include_directories(/usr/local/include)

add_executable(Ass1 main.cpp rasterizer.hpp rasterizer.cpp Triangle.hpp Triangle.cpp)
target_link_libraries(Ass1 ${OpenCV_LIBRARIES})
