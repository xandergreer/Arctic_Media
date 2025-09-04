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
                    'Connection Failed',
                    'Could not connect to the server. Please check:\n\n• The URL is correct\n• The server is running\n• Your network connection\n\nExamples:\n• 192.168.1.100:8000\n• arcticmedia.space\n• myserver.local:8080'
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
                    <Text style={styles.title}>Arctic Media</Text>
                    <Text style={styles.subtitle}>Connect to your media server</Text>

                    <View style={styles.form}>
                        <Text style={styles.label}>Server URL or Domain</Text>
                        <TextInput
                            style={styles.input}
                            placeholder="e.g., arcticmedia.space or 192.168.1.100:8000"
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
                        <Text style={styles.examplesTitle}>Examples:</Text>
                        <View style={styles.exampleButtons}>
                            <TouchableOpacity
                                style={styles.exampleButton}
                                onPress={() => handleExamplePress('arcticmedia.space')}
                            >
                                <Text style={styles.exampleButtonText}>arcticmedia.space</Text>
                            </TouchableOpacity>

                            <TouchableOpacity
                                style={styles.exampleButton}
                                onPress={() => handleExamplePress('192.168.1.100:8000')}
                            >
                                <Text style={styles.exampleButtonText}>192.168.1.100:8000</Text>
                            </TouchableOpacity>

                            <TouchableOpacity
                                style={styles.exampleButton}
                                onPress={() => handleExamplePress('localhost:8000')}
                            >
                                <Text style={styles.exampleButtonText}>localhost:8000</Text>
                            </TouchableOpacity>
                        </View>
                    </View>

                    <View style={styles.help}>
                        <Text style={styles.helpTitle}>Need help?</Text>
                        <Text style={styles.helpText}>
                            • Enter your server's IP address and port (e.g., 192.168.1.100:8000)
                        </Text>
                        <Text style={styles.helpText}>
                            • Or use your domain name if you have one
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
