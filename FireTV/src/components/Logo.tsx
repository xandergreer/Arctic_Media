import React from 'react';
import { SvgXml } from 'react-native-svg';
import { View, StyleSheet } from 'react-native';

// SVG logo content - using the logo-mark-icecap-cutout.svg
const logoXml = `
<svg xmlns="http://www.w3.org/2000/svg" width="160" height="160" viewBox="0 0 64 64">
  <defs>
    <linearGradient id="am_g3c_mark" x1="0" y1="1" x2="1" y2="0">
      <stop offset="0" stop-color="#5bc0ff"/><stop offset="1" stop-color="#2a6bff"/>
    </linearGradient>
  </defs>
  <g transform="translate(6,0)">
    <path fill="url(#am_g3c_mark)" fill-rule="evenodd"
          d="M26 6 L52 58 H40 L34 44 L26 54 L18 44 L12 58 H0 Z
             M26 26 L34 40 L18 40 Z"/>
    <path d="M18 22 L26 6 L34 22 Z" fill="#EAF5FF" opacity=".95"/>
  </g>
</svg>
`;

interface LogoProps {
  width?: number;
  height?: number;
}

export default function Logo({ width = 120, height = 120 }: LogoProps) {
  return (
    <View style={styles.container}>
      <SvgXml xml={logoXml} width={width} height={height} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
    justifyContent: 'center',
  },
});

