import {spawn} from 'child_process';
import {resolve} from 'path';

const NODE_MARKER = 'What version of nodejs do you want to install?';
const TOOL_NAME_MARKER = 'What tool do you want to install?';
const TOOL_VERSION_MARKER = 'What version of npm do you want to install?';

function runDockerInstallTest(
  responseFn: (respond: (question: string, response: string) => void) => void,
  filename: string,
  done: (error?: Error | string, fileContents?: string) => void
) {
  const currentDir = resolve(__dirname, '..');
  const containerName = `ntw-test-${Date.now()}-${Math.random().toString(36).substring(7)}`;

  // Create and start container
  const dockerProcess = spawn('docker', [
    'run', '--name', containerName, '-i',
    '-v', `${currentDir}:/ntw`,
    '-w', '/workspace',
    'ntw-test',
    '/ntw/install.sh'
  ], {
    stdio: ['pipe', 'pipe', 'pipe']
  });

  let outputBuffer = '';

  function respond(question: string, response: string) {
    if (outputBuffer.includes(question)) {
      dockerProcess.stdin?.write(response + '\n');
      outputBuffer = '';
    }
  }

  dockerProcess.stdout?.on('data', (data: Buffer) => {
    const output = data.toString();
    outputBuffer += output;
    process.stdout.write(output); // Show output for visibility

    // Execute the response logic
    responseFn(respond);
  });

  dockerProcess.stderr?.on('data', (data: Buffer) => {
    process.stderr.write(data); // Show stderr for debugging
  });

  dockerProcess.on('close', (code) => {
    if (code === 0) {
      // Copy the file from the stopped container
      const cpProcess = spawn('docker', [
        'cp', `${containerName}:/workspace/${filename}`, '-'
      ]);

      let fileContents = '';
      cpProcess.stdout?.on('data', (data: Buffer) => {
        fileContents += data.toString();
      });

      cpProcess.on('close', (cpCode) => {
        // Clean up container
        spawn('docker', ['rm', containerName]);

        if (cpCode === 0) {
          done(undefined, fileContents);
        } else {
          done(new Error(`Failed to copy file ${filename} from container`));
        }
      });

      cpProcess.on('error', (error) => {
        // Clean up container on error
        spawn('docker', ['rm', containerName]);
        done(error);
      });
    } else {
      // Clean up container on error
      spawn('docker', ['rm', containerName]);
      done(new Error(`Docker process exited with code ${code}`));
    }
  });

  dockerProcess.on('error', (error) => {
    // Clean up container on error
    spawn('docker', ['rm', containerName]);
    done(error);
  });
}

describe('install.sh', () => {
  test('should run successfully in Docker container and create npmw', (done) => {
    runDockerInstallTest((respond) => {
      respond(NODE_MARKER, '22.0.0');
      respond(TOOL_NAME_MARKER, 'npm');
      respond(TOOL_VERSION_MARKER, '10.0.0');
    }, 'npmw', (error, fileContents) => {
      if (error) {
        done(error);
        return;
      }

      expect(fileContents).toBeDefined();
      expect(fileContents).toContain('#!/bin/bash');
      expect(fileContents).toContain('selectNode v22.0.0');
      expect(fileContents).toContain('selectTool npm 10.0.0');
      expect(fileContents).toContain('npm "$@"');
      done();
    });
  }, 30000);

  test('should handle yarn installation and create yarnw', (done) => {
    runDockerInstallTest((respond) => {
      respond(NODE_MARKER, '20.0.0');
      respond(TOOL_NAME_MARKER, 'yarn');
      respond('What version of yarn do you want to install?', '4.0.0');
    }, 'yarnw', (error, fileContents) => {
      if (error) {
        done(error);
        return;
      }

      expect(fileContents).toBeDefined();
      expect(fileContents).toContain('#!/bin/bash');
      expect(fileContents).toContain('selectNode v20.0.0');
      expect(fileContents).toContain('selectTool yarn 4.0.0');
      expect(fileContents).toContain('yarn "$@"');
      done();
    });
  }, 30000);

  test('should handle node installation and create nodew', (done) => {
    runDockerInstallTest((respond) => {
      respond(NODE_MARKER, '20.0.0');
      respond(TOOL_NAME_MARKER, 'node');
      // respond('What version of yarn do you want to install?', '4.0.0');
    }, 'nodew', (error, fileContents) => {
      if (error) {
        done(error);
        return;
      }

      expect(fileContents).toBeDefined();
      expect(fileContents).toContain('#!/bin/bash');
      expect(fileContents).toContain('selectNode v20.0.0');
      // expect(fileContents).toContain('selectTool yarn 4.0.0');
      expect(fileContents).toContain('node "$@"');
      done();
    });
  }, 30000);
});
