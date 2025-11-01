import React, { useState, useEffect } from 'react';
import {
    View,
    Text,
    TextInput,
    TouchableOpacity,
    StyleSheet,
    Alert,
    ActivityIndicator,
    KeyboardAvoidingView,
    Platform,
    ScrollView,
} from 'react-native';
import { useAuthStore } from '../store/authStore';
import Logo from '../components/Logo';

export default function ServerConfigScreen() {
    const [serverUrl, setServerUrl] = useState('');
    const [isValidating, setIsValidating] = useState(false);
    const [isLoading, setIsLoading] = useState(true);
    const { validateServer, serverConfig } = useAuthStore();

    useEffect(() => {
        // Check if we already have a server config
        if (serverConfig) {
            // If we have a config, we'll navigate automatically
            return;
        }
        setIsLoading(false);
    }, [serverConfig]);

    const handleConnect = async () => {
        if (!serverUrl.trim()) {
            Alert.alert('Error', 'Please enter a server URL or domain');
            return;
        }

        setIsValidating(true);
        try {
            const isValid = await validateServer(serverUrl);
            if (isValid) {
                // Server is valid, navigation will happen automatically
                // through the AppNavigator based on state changes
            } else {
                Alert.alert(
                    'Connection Failed - Request Timed Out',
                    'The app cannot reach the server.\n\n⚠️ Using Expo Go - Test in Safari First:\n1. Open Safari on your iPhone\n2. Visit: https://arcticmedia.space/health\n\n📱 Expo Go Limitations:\n• Network security settings may be restricted\n• Some domains may not work\n• Try using IP address instead\n\n🔧 Troubleshooting:\n\nIf Safari works:\n• Restart Expo Go app\n• Clear Expo Go cache\n• Try IP address: 192.168.x.x:8000\n• Consider development build\n\nIf Safari also fails:\n• Check WiFi/network connection\n• Verify device/server same network\n• Try different network\n• Check DNS resolution\n\n💡 Tip: For Expo Go, try your server\'s local IP address instead of the domain name.'
                );
            }
        } catch (error) {
            Alert.alert('Error', 'Failed to validate server. Please try again.');
        } finally {
            setIsValidating(false);
        }
    };

    const handleExamplePress = (example: string) => {
        setServerUrl(example);
    };

    if (isLoading) {
        return (
            <View style={styles.loadingContainer}>
                <ActivityIndicator size="large" color="#007AFF" />
                <Text style={styles.loadingText}>Loading...</Text>
            </View>
        );
    }

    return (
        <KeyboardAvoidingView
            style={styles.container}
            behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        >
            <ScrollView contentContainerStyle={styles.scrollContent}>
                <View style={styles.content}>
                    <View style={styles.logoContainer}>
                        <Logo width={120} height={120} />
                    </View>
                    <Text style={styles.title}>Arctic Media</Text>
                    <Text style={styles.subtitle}>Connect to your media server</Text>

                    <View style={styles.form}>
                        <Text style={styles.label}>Server IP Address (Local Network)</Text>
                        <TextInput
                            style={styles.input}
                            placeholder="e.g., 192.168.1.100:8000 (use local IP, not domain)"
                            placeholderTextColor="#666"
                            value={serverUrl}
                            onChangeText={setServerUrl}
                            autoCapitalize="none"
                            autoCorrect={false}
                            autoComplete="off"
                        />

                        <TouchableOpacity
                            style={[styles.button, isValidating && styles.buttonDisabled]}
                            onPress={handleConnect}
                            disabled={isValidating}
                        >
                            {isValidating ? (
                                <View style={styles.buttonContent}>
                                    <ActivityIndicator size="small" color="#ffffff" />
                                    <Text style={styles.buttonText}>Connecting...</Text>
                                </View>
                            ) : (
                                <Text style={styles.buttonText}>Connect</Text>
                            )}
                        </TouchableOpacity>
                    </View>

                        <View style={styles.examples}>
                        <Text style={styles.examplesTitle}>Recommended: Use Local IP Address</Text>
                        <View style={styles.exampleButtons}>
                            <TouchableOpacity
                                style={styles.exampleButton}
                                onPress={() => handleExamplePress('192.168.1.100:8000')}
                            >
                                <Text style={styles.exampleButtonText}>192.168.1.100:8000</Text>
                            </TouchableOpacity>

                            <TouchableOpacity
                                style={styles.exampleButton}
                                onPress={() => handleExamplePress('192.168.0.100:8000')}
                            >
                                <Text style={styles.exampleButtonText}>192.168.0.100:8000</Text>
                            </TouchableOpacity>

                            <TouchableOpacity
                                style={styles.exampleButton}
                                onPress={() => handleExamplePress('10.0.0.100:8000')}
                            >
                                <Text style={styles.exampleButtonText}>10.0.0.100:8000</Text>
                            </TouchableOpacity>
                        </View>
                        <Text style={styles.examplesNote}>
                            💡 Tip: Find your server's IP by checking your router admin page or running "ipconfig" (Windows) / "ifconfig" (Mac/Linux) on the server computer.
                        </Text>
                    </View>

                    <View style={styles.help}>
                        <Text style={styles.helpTitle}>Need help?</Text>
                        <Text style={styles.helpText}>
                            • Use your server's LOCAL IP address (e.g., 192.168.1.100:8000)
                        </Text>
                        <Text style={styles.helpText}>
                            • Domains may not work on local WiFi - use IP address instead
                        </Text>
                        <Text style={styles.helpText}>
                            • Find your server's IP: Check your router or run ipconfig/ifconfig on server
                        </Text>
                        <Text style={styles.helpText}>
                            • Make sure your Arctic Media server is running
                        </Text>
                    </View>
                </View>
            </ScrollView>
        </KeyboardAvoidingView>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: '#000000',
    },
    loadingContainer: {
        flex: 1,
        justifyContent: 'center',
        alignItems: 'center',
        backgroundColor: '#000000',
    },
    loadingText: {
        color: '#ffffff',
        fontSize: 18,
        marginTop: 16,
    },
    scrollContent: {
        flexGrow: 1,
        justifyContent: 'center',
    },
    content: {
        paddingHorizontal: 40,
        paddingVertical: 20,
    },
    logoContainer: {
        alignItems: 'center',
        marginBottom: 20,
    },
    title: {
        fontSize: 48,
        fontWeight: 'bold',
        color: '#ffffff',
        marginBottom: 20,
        textAlign: 'center',
    },
    subtitle: {
        fontSize: 18,
        color: '#cccccc',
        marginBottom: 60,
        textAlign: 'center',
    },
    form: {
        width: '100%',
        maxWidth: 500,
        alignSelf: 'center',
        marginBottom: 40,
    },
    label: {
        fontSize: 16,
        color: '#ffffff',
        marginBottom: 8,
        fontWeight: '600',
    },
    input: {
        backgroundColor: '#1a1a1a',
        borderWidth: 2,
        borderColor: '#333333',
        borderRadius: 8,
        padding: 16,
        fontSize: 18,
        color: '#ffffff',
        marginBottom: 20,
    },
    button: {
        backgroundColor: '#007AFF',
        borderRadius: 8,
        padding: 16,
        alignItems: 'center',
    },
    buttonDisabled: {
        backgroundColor: '#666666',
    },
    buttonContent: {
        flexDirection: 'row',
        alignItems: 'center',
    },
    buttonText: {
        color: '#ffffff',
        fontSize: 18,
        fontWeight: 'bold',
        marginLeft: 8,
    },
    examples: {
        marginBottom: 40,
    },
    examplesTitle: {
        fontSize: 16,
        color: '#cccccc',
        marginBottom: 16,
        textAlign: 'center',
    },
    exampleButtons: {
        flexDirection: 'row',
        justifyContent: 'center',
        flexWrap: 'wrap',
        gap: 12,
    },
    exampleButton: {
        backgroundColor: '#1a1a1a',
        borderWidth: 1,
        borderColor: '#333333',
        borderRadius: 6,
        paddingHorizontal: 16,
        paddingVertical: 8,
    },
    exampleButtonText: {
        color: '#007AFF',
        fontSize: 14,
        fontWeight: '500',
    },
    examplesNote: {
        fontSize: 12,
        color: '#999999',
        marginTop: 12,
        textAlign: 'center',
        fontStyle: 'italic',
        paddingHorizontal: 20,
    },
    help: {
        backgroundColor: '#1a1a1a',
        borderRadius: 12,
        padding: 20,
        borderWidth: 1,
        borderColor: '#333333',
    },
    helpTitle: {
        fontSize: 18,
        color: '#ffffff',
        fontWeight: 'bold',
        marginBottom: 12,
    },
    helpText: {
        fontSize: 14,
        color: '#cccccc',
        marginBottom: 8,
        lineHeight: 20,
    },
});
