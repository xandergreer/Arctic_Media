import React, { useState } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Modal,
} from 'react-native';

export type GridDensity = 2 | 3 | 4;

interface OptionsMenuProps {
  density: GridDensity;
  onDensityChange: (density: GridDensity) => void;
}

export default function OptionsMenu({ density, onDensityChange }: OptionsMenuProps) {
  const [visible, setVisible] = useState(false);
  const densities: GridDensity[] = [2, 3, 4];

  const handleDensityChange = (newDensity: GridDensity) => {
    onDensityChange(newDensity);
    setVisible(false);
  };

  return (
    <>
      <TouchableOpacity onPress={() => setVisible(true)} style={styles.button}>
        <Text style={styles.buttonText}>⋯</Text>
      </TouchableOpacity>
      
      <Modal
        visible={visible}
        transparent
        animationType="fade"
        onRequestClose={() => setVisible(false)}
      >
        <TouchableOpacity
          style={styles.backdrop}
          activeOpacity={1}
          onPress={() => setVisible(false)}
        >
          <View style={styles.menu}>
            <View style={styles.menuHeader}>
              <Text style={styles.menuHeaderText}>Options</Text>
            </View>
            
            <View style={styles.menuSection}>
              <Text style={styles.menuSectionTitle}>Grid Layout</Text>
              {densities.map((d) => (
                <TouchableOpacity
                  key={d}
                  style={styles.menuItem}
                  onPress={() => handleDensityChange(d)}
                >
                  <View style={styles.menuItemContent}>
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
                    <Text style={[styles.menuItemText, density === d && styles.menuItemTextActive]}>
                      {d} columns
                    </Text>
                  </View>
                  {density === d && (
                    <Text style={styles.checkmark}>✓</Text>
                  )}
                </TouchableOpacity>
              ))}
            </View>
          </View>
        </TouchableOpacity>
      </Modal>
    </>
  );
}

const styles = StyleSheet.create({
  button: {
    padding: 8,
    marginRight: 8,
  },
  buttonText: {
    fontSize: 24,
    color: '#ffffff',
    fontWeight: 'bold',
    lineHeight: 24,
  },
  backdrop: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    justifyContent: 'flex-end',
  },
  menu: {
    backgroundColor: '#1a1a1a',
    borderTopLeftRadius: 16,
    borderTopRightRadius: 16,
    paddingBottom: 32,
  },
  menuHeader: {
    padding: 20,
    borderBottomWidth: 1,
    borderBottomColor: '#333333',
  },
  menuHeaderText: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#ffffff',
  },
  menuSection: {
    padding: 20,
  },
  menuSectionTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: '#999999',
    marginBottom: 12,
    textTransform: 'uppercase',
  },
  menuItem: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: 12,
    paddingHorizontal: 4,
  },
  menuItemContent: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  menuItemText: {
    fontSize: 16,
    color: '#ffffff',
  },
  menuItemTextActive: {
    color: '#007AFF',
    fontWeight: '600',
  },
  gridPattern: {
    flexDirection: 'row',
    gap: 4,
  },
  gridDot: {
    width: 5,
    height: 5,
    borderRadius: 2.5,
    backgroundColor: '#666666',
  },
  gridDotActive: {
    backgroundColor: '#007AFF',
  },
  checkmark: {
    fontSize: 18,
    color: '#007AFF',
    fontWeight: 'bold',
  },
});
