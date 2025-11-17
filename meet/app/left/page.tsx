'use client';
import React from 'react';
import styles from '../../styles/Home.module.css'; // <-- Correct relative path

export default function LeftPage() {
  return (
    <main className={styles.main}>
      <div className={styles.tabContent}>
        <h1>Thank you for joining!</h1>
        <p>We appreciate your participation in the meeting.</p>
        <p>You can now safely close this tab or return to the home page.</p>
      </div>
    </main>
  );
}
