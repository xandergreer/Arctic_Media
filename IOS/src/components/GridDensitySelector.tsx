import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';

export type GridDensity = 2 | 3 | 4;

interface GridDensitySelectorProps {
  density: GridDensity;
  onDensityChange: (density: GridDensity) => void;
}

export default function GridDensitySelector({ density, onDensityChange }: GridDensitySelectorProps) {
  const densities: GridDensity[] = [2, 3, 4];
  
  return (
    <View style={styles.container}>
      {densities.map((d) => (
        <TouchableOpacity
          key={d}
          style={[
            styles.button,
            density === d && styles.buttonActive,
          ]}
          onPress={() => onDensityChange(d)}
        >
          <View style={styles.gridPattern}>
            {Array.from({ length: d }).map((_, i) => (
              <View
                key={i}
                style={[
                  styles.gridDot,
                  density === d && styles.gridDotActive,
                ]}
              />
            ))}
          </View>
        </TouchableOpacity>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  button: {
    padding: 8,
    borderRadius: 6,
    backgroundColor: '#1a1a1a',
    borderWidth: 1,
    borderColor: '#333333',
  },
  buttonActive: {
    backgroundColor: '#007AFF',
    borderColor: '#007AFF',
  },
  gridPattern: {
    flexDirection: 'row',
    gap: 3,
  },
  gridDot: {
    width: 4,
    height: 4,
    borderRadius: 2,
    backgroundColor: '#666666',
  },
  gridDotActive: {
    backgroundColor: '#ffffff',
  },
});
