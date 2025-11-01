import React from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Modal,
  Animated,
  Dimensions,
} from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { StackNavigationProp } from '@react-navigation/stack';
import { RootStackParamList } from '../navigation/AppNavigator';
import { useAuthStore } from '../store/authStore';

type DrawerMenuNavigationProp = StackNavigationProp<RootStackParamList>;

const { width } = Dimensions.get('window');
const DRAWER_WIDTH = width * 0.75;

interface DrawerMenuProps {
  visible: boolean;
  onClose: () => void;
}

export default function DrawerMenu({ visible, onClose }: DrawerMenuProps) {
  const navigation = useNavigation<DrawerMenuNavigationProp>();
  const { user, logout, serverConfig, clearServerConfig } = useAuthStore();
  const slideAnim = React.useRef(new Animated.Value(-DRAWER_WIDTH)).current;

  React.useEffect(() => {
    if (visible) {
      Animated.timing(slideAnim, {
        toValue: 0,
        duration: 300,
        useNativeDriver: true,
      }).start();
    } else {
      Animated.timing(slideAnim, {
        toValue: -DRAWER_WIDTH,
        duration: 300,
        useNativeDriver: true,
      }).start();
    }
  }, [visible, slideAnim]);

  const handleNavigate = (screen: keyof RootStackParamList) => {
    onClose();
    navigation.navigate(screen as any);
  };

  const handleLogout = async () => {
    onClose();
    await logout();
  };

  const handleChangeServer = () => {
    onClose();
    clearServerConfig();
  };

  return (
    <Modal
      visible={visible}
      transparent
      animationType="none"
      onRequestClose={onClose}
    >
      <View style={styles.container}>
        <TouchableOpacity
          style={styles.backdrop}
          activeOpacity={1}
          onPress={onClose}
        />
        <Animated.View
          style={[
            styles.drawer,
            {
              transform: [{ translateX: slideAnim }],
            },
          ]}
        >
          <View style={styles.header}>
            <Text style={styles.headerTitle}>Arctic Media</Text>
            <TouchableOpacity onPress={onClose} style={styles.closeButton}>
              <Text style={styles.closeButtonText}>✕</Text>
            </TouchableOpacity>
          </View>

          <View style={styles.userSection}>
            <Text style={styles.userName}>{user?.username || 'User'}</Text>
            <Text style={styles.serverUrl} numberOfLines={1}>
              {serverConfig?.url}
            </Text>
          </View>

          <View style={styles.menuSection}>
            <MenuItem
              icon="🏠"
              title="Home"
              onPress={() => handleNavigate('Home')}
            />
            <MenuItem
              icon="📺"
              title="TV Shows"
              onPress={() => handleNavigate('TVShows')}
            />
            <MenuItem
              icon="🎬"
              title="Movies"
              onPress={() => handleNavigate('Movies')}
            />
            <MenuItem
              icon="⚙️"
              title="Settings"
              onPress={() => handleNavigate('Settings')}
            />
          </View>

          <View style={styles.footer}>
            <TouchableOpacity
              style={styles.footerButton}
              onPress={handleChangeServer}
            >
              <Text style={styles.footerButtonText}>Change Server</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={[styles.footerButton, styles.logoutButton]}
              onPress={handleLogout}
            >
              <Text style={styles.footerButtonText}>Logout</Text>
            </TouchableOpacity>
          </View>
        </Animated.View>
      </View>
    </Modal>
  );
}

interface MenuItemProps {
  icon: string;
  title: string;
  onPress: () => void;
}

function MenuItem({ icon, title, onPress }: MenuItemProps) {
  return (
    <TouchableOpacity style={styles.menuItem} onPress={onPress}>
      <Text style={styles.menuIcon}>{icon}</Text>
      <Text style={styles.menuTitle}>{title}</Text>
      <Text style={styles.menuArrow}>›</Text>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    flexDirection: 'row',
  },
  backdrop: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
  },
  drawer: {
    width: DRAWER_WIDTH,
    backgroundColor: '#1a1a1a',
    shadowColor: '#000',
    shadowOffset: { width: 2, height: 0 },
    shadowOpacity: 0.3,
    shadowRadius: 4,
    elevation: 5,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 20,
    paddingTop: 60,
    borderBottomWidth: 1,
    borderBottomColor: '#333333',
  },
  headerTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#ffffff',
  },
  closeButton: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: '#333333',
    justifyContent: 'center',
    alignItems: 'center',
  },
  closeButtonText: {
    color: '#ffffff',
    fontSize: 18,
    fontWeight: 'bold',
  },
  userSection: {
    padding: 20,
    borderBottomWidth: 1,
    borderBottomColor: '#333333',
  },
  userName: {
    fontSize: 18,
    fontWeight: '600',
    color: '#ffffff',
    marginBottom: 4,
  },
  serverUrl: {
    fontSize: 12,
    color: '#999999',
  },
  menuSection: {
    paddingVertical: 10,
  },
  menuItem: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
    paddingHorizontal: 20,
    borderBottomWidth: 1,
    borderBottomColor: '#252525',
  },
  menuIcon: {
    fontSize: 24,
    marginRight: 16,
    width: 32,
  },
  menuTitle: {
    flex: 1,
    fontSize: 16,
    fontWeight: '500',
    color: '#ffffff',
  },
  menuArrow: {
    fontSize: 20,
    color: '#666666',
  },
  footer: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    padding: 20,
    borderTopWidth: 1,
    borderTopColor: '#333333',
  },
  footerButton: {
    backgroundColor: '#333333',
    padding: 14,
    borderRadius: 8,
    marginBottom: 10,
    alignItems: 'center',
  },
  logoutButton: {
    backgroundColor: '#FF3B30',
  },
  footerButtonText: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: '600',
  },
});

