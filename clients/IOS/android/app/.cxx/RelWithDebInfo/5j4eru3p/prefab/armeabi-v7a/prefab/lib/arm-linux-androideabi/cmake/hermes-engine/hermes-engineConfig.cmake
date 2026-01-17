if(NOT TARGET hermes-engine::libhermes)
add_library(hermes-engine::libhermes SHARED IMPORTED)
set_target_properties(hermes-engine::libhermes PROPERTIES
    IMPORTED_LOCATION "C:/Users/thebo/.gradle/caches/8.14.3/transforms/5c678b73e2f69303c6df5ba1020627c5/transformed/hermes-android-0.81.5-release/prefab/modules/libhermes/libs/android.armeabi-v7a/libhermes.so"
    INTERFACE_INCLUDE_DIRECTORIES "C:/Users/thebo/.gradle/caches/8.14.3/transforms/5c678b73e2f69303c6df5ba1020627c5/transformed/hermes-android-0.81.5-release/prefab/modules/libhermes/include"
    INTERFACE_LINK_LIBRARIES ""
)
endif()

