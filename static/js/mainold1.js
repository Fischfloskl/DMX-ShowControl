import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { TransformControls } from 'three/addons/controls/TransformControls.js';

console.log("Three.js Version:", THREE.REVISION);


// ============================================================
// GRUNDSETUP
// ============================================================

const sceneContainer =
    document.getElementById("scene");

const scene =
    new THREE.Scene();

scene.background =
    new THREE.Color(0x101010);

let projectChanged = false;


// ============================================================
// KAMERA
// ============================================================

const camera =
    new THREE.PerspectiveCamera(

        50,

        sceneContainer.clientWidth /
        sceneContainer.clientHeight,

        0.1,

        1000
    );

camera.position.set(
    8,
    7,
    10
);


// ============================================================
// WARNUNG BEIM SCHLIESSEN
// ============================================================

window.addEventListener(
    "beforeunload",
    event => {

        if (!projectChanged) {
            return;
        }

        event.preventDefault();

        event.returnValue = "";

    }
);


// ============================================================
// MOBILE / TABLET WARNUNG
// ============================================================

const isMobile =
    /Android|iPhone|iPad|iPod|Windows Phone/i.test(navigator.userAgent) ||
    window.innerWidth < 1200;

if (isMobile) {

    const warning =
        document.getElementById("desktopWarning");

    if (warning) {
        warning.style.display = "flex";
    }
}


// ============================================================
// RENDERER
// ============================================================

const renderer =
    new THREE.WebGLRenderer({

        antialias: true

    });

renderer.setPixelRatio(
    window.devicePixelRatio
);

renderer.setSize(

    sceneContainer.clientWidth,

    sceneContainer.clientHeight

);

renderer.shadowMap.enabled = true;

sceneContainer.appendChild(
    renderer.domElement
);


// ============================================================
// ORBIT CONTROLS
// ============================================================

const controls =
    new OrbitControls(
        camera,
        renderer.domElement
    );

controls.target.set(
    0,
    1,
    0
);

controls.enableDamping = true;


// ============================================================
// TRANSFORM CONTROLS
// ============================================================

const transformControls =
    new TransformControls(
        camera,
        renderer.domElement
    );

transformControls.setMode(
    "translate"
);

transformControls.setSpace(
    "world"
);

transformControls.setSize(
    0.9
);

scene.add(
    transformControls.getHelper()
);


// ============================================================
// TRANSFORM / ORBIT ZUSAMMENARBEIT
// ============================================================

transformControls.addEventListener(
    "dragging-changed",
    event => {

        controls.enabled =
            !event.value;

        if (event.value) {

            beginUndoAction();

        } else {

            endUndoAction();

        }

    }
);


// ============================================================
// GRUNDBELEUCHTUNG
// ============================================================

const ambientLight =
    new THREE.AmbientLight(
        0xffffff,
        0
    );

scene.add(
    ambientLight
);


const roomLight =
    new THREE.DirectionalLight(
        0xffffff,
        0.3
    );

roomLight.position.set(
    5,
    10,
    5
);

roomLight.castShadow = true;

scene.add(
    roomLight
);


// ============================================================
// UNIVERSUM
// ============================================================

let universeSize = 30;


// ============================================================
// BODEN
// ============================================================

const floorMaterial =
    new THREE.MeshStandardMaterial({

        color: 0x292929,

        roughness: 0.8

    });


const floor =
    new THREE.Mesh(

        new THREE.PlaneGeometry(
            universeSize,
            universeSize
        ),

        floorMaterial

    );

floor.rotation.x =
    -Math.PI / 2;

floor.receiveShadow = true;

scene.add(
    floor
);


// ============================================================
// RASTER
// ============================================================

let grid =
    new THREE.GridHelper(

        universeSize,

        universeSize,

        0x555555,

        0x333333

    );

grid.position.y =
    0.01;

scene.add(
    grid
);


// ============================================================
// UNIVERSUM GRÖSSE ÄNDERN
// ============================================================

function updateUniverseSize(
    size
) {

    universeSize =
        size;


    // ----------------------------------------
    // Boden
    // ----------------------------------------

    floor.geometry.dispose();

    floor.geometry =
        new THREE.PlaneGeometry(
            universeSize,
            universeSize
        );


    // ----------------------------------------
    // Raster
    // ----------------------------------------

    scene.remove(
        grid
    );

    grid.geometry.dispose();

    if (Array.isArray(grid.material)) {

        grid.material.forEach(
            material => material.dispose()
        );

    } else {

        grid.material.dispose();

    }


    grid =
        new THREE.GridHelper(

            universeSize,

            Math.round(universeSize),

            0x555555,

            0x333333

        );

    grid.position.y =
        0.01;

    scene.add(
        grid
    );
}


// ============================================================
// ACHSEN
// ============================================================

const axes =
    new THREE.AxesHelper(2);

scene.add(
    axes
);


// ============================================================
// FIXTURE STORAGE
// ============================================================

let fixtures = [];

let selectedFixture = null;

let fixtureCounter = 0;

let copiedSettings = null;


// ============================================================
// UNDO / REDO
// ============================================================

let undoStack = [];
let redoStack = [];

const MAX_UNDO_STEPS = 50;

let historyActionOpen = false;


// ============================================================
// POSITIONS-INPUTS
// ============================================================

const xInput =
    document.getElementById("xInput");

const yInput =
    document.getElementById("yInput");

const zInput =
    document.getElementById("zInput");


// ============================================================
// GLOBAL BEAM
// ============================================================

let globalBeamLength = 5;

let globalBeamsVisible = true;


// ============================================================
// MOVING HEAD KLASSE
// ============================================================

class MovingHead {

    constructor(
        id,
        position = new THREE.Vector3()
    ) {

        this.id =
            id;


        // ----------------------------------------
        // HAUPTGRUPPE
        // ----------------------------------------

        this.group =
            new THREE.Group();

        this.group.position.copy(
            position
        );

        scene.add(
            this.group
        );


        // ----------------------------------------
        // BASIS
        // ----------------------------------------

        const baseGeometry =
            new THREE.CylinderGeometry(

                0.14,
                0.14,
                0.14,
                24

            );


        const baseMaterial =
            new THREE.MeshStandardMaterial({

                color: 0x202020,

                metalness: 0.7,

                roughness: 0.35

            });


        this.base =
            new THREE.Mesh(

                baseGeometry,

                baseMaterial

            );

        this.base.position.y =
            0.05;

        this.base.castShadow =
            true;

        this.group.add(
            this.base
        );


        // ----------------------------------------
        // PAN
        // ----------------------------------------

        this.panGroup =
            new THREE.Group();

        this.panGroup.position.y =
            0.10;

        this.group.add(
            this.panGroup
        );


        // ----------------------------------------
        // BÜGEL
        // ----------------------------------------

        const yokeGeometry =
            new THREE.BoxGeometry(

                0.045,
                0.35,
                0.045

            );


        const yokeMaterial =
            new THREE.MeshStandardMaterial({

                color: 0x333333,

                metalness: 0.7

            });


        const yokeLeft =
            new THREE.Mesh(

                yokeGeometry,

                yokeMaterial

            );

        yokeLeft.position.set(
            -0.12,
            0.15,
            0
        );

        this.panGroup.add(
            yokeLeft
        );


        const yokeRight =
            new THREE.Mesh(

                yokeGeometry,

                yokeMaterial

            );

        yokeRight.position.set(
            0.12,
            0.15,
            0
        );

        this.panGroup.add(
            yokeRight
        );


        // ----------------------------------------
        // TILT
        // ----------------------------------------

        this.tiltGroup =
            new THREE.Group();

        this.tiltGroup.position.y =
            0.32;

        this.panGroup.add(
            this.tiltGroup
        );


        // ----------------------------------------
        // KOPF
        // ----------------------------------------

        const headGeometry =
            new THREE.BoxGeometry(
                0.20,
                0.20,
                0.30
            );


        const headMaterial =
            new THREE.MeshStandardMaterial({

                color: 0x444444,

                metalness: 0.65,

                roughness: 0.3

            });


        this.head =
            new THREE.Mesh(

                headGeometry,

                headMaterial

            );

        this.head.castShadow =
            true;

        this.tiltGroup.add(
            this.head
        );


        // ----------------------------------------
        // LINSE
        // ----------------------------------------

        const lensGeometry =
            new THREE.CircleGeometry(
                0.085,
                32
            );


        this.lensMaterial =
            new THREE.MeshBasicMaterial({

                color: 0xffffff,

                side: THREE.DoubleSide

            });


        this.lens =
            new THREE.Mesh(

                lensGeometry,

                this.lensMaterial

            );


        this.lens.position.z =
            0.155;


        this.lens.rotation.y =
            0;


        this.tiltGroup.add(
            this.lens
        );


        // ----------------------------------------
        // ECHTES THREE.JS LICHT
        // ----------------------------------------

        this.light =
            new THREE.SpotLight(

                0xffffff,

                5,

                globalBeamLength,

                THREE.MathUtils.degToRad(20),

                0.45,

                1

            );


        this.light.castShadow =
            true;


        this.light.position.set(

            0,
            0,
            0.15

        );


        this.tiltGroup.add(
            this.light
        );


        // ----------------------------------------
        // LICHTZIEL
        // ----------------------------------------

        this.lightTarget =
            new THREE.Object3D();


        this.lightTarget.position.set(

            0,
            0,
            globalBeamLength

        );


        this.tiltGroup.add(
            this.lightTarget
        );


        this.light.target =
            this.lightTarget;


        // ----------------------------------------
        // SICHTBARER BEAM
        // ----------------------------------------

        this.beam =
            this.createBeam();


        this.tiltGroup.add(
            this.beam
        );


        // ----------------------------------------
        // STANDARDWERTE
        // ----------------------------------------

        this.pan =
            0;

        this.tilt =
            0;

        this.color =
            "#ffffff";

        this.intensity =
            5;

        this.angle =
            20;


        this.update();
    }


    // ========================================================
    // BEAM ERSTELLEN
    // ========================================================

    createBeam() {

        const geometry =
            new THREE.ConeGeometry(

                1,
                1,
                48,
                1,
                true

            );


        const material =
            new THREE.MeshBasicMaterial({

                color: 0xffffff,

                transparent: true,

                opacity: 0.12,

                depthWrite: false,

                side: THREE.DoubleSide,

                blending:
                    THREE.AdditiveBlending

            });


        const beam =
            new THREE.Mesh(

                geometry,

                material

            );


        beam.rotation.x =
            -Math.PI / 2;


        return beam;
    }


    // ========================================================
    // UPDATE
    // ========================================================

    update() {

        // ----------------------------------------
        // PAN
        // ----------------------------------------

        this.panGroup.rotation.y =
            THREE.MathUtils.degToRad(
                this.pan
            );


        // ----------------------------------------
        // TILT - REVERSED
        // ----------------------------------------

        this.tiltGroup.rotation.x =
            -THREE.MathUtils.degToRad(
                this.tilt
            );


        // ----------------------------------------
        // FARBE
        // ----------------------------------------

        const color =
            new THREE.Color(
                this.color
            );


        this.light.color.copy(
            color
        );


        this.lensMaterial.color.copy(
            color
        );


        this.beam.material.color.copy(
            color
        );


        // ----------------------------------------
        // INTENSITÄT
        // ----------------------------------------

        this.light.intensity =
            this.intensity;


        // ----------------------------------------
        // BEAM ANGLE
        // ----------------------------------------

        this.light.angle =
            THREE.MathUtils.degToRad(
                this.angle
            );


        // ----------------------------------------
        // BEAM LÄNGE
        // ----------------------------------------

        const beamLength =
            globalBeamLength;


        this.light.distance =
            beamLength;


        // ----------------------------------------
        // SICHTBARKEIT
        // ----------------------------------------

        this.beam.visible =
            globalBeamsVisible;


        // ----------------------------------------
        // BEAM RADIUS
        // ----------------------------------------

        const radius =
            Math.tan(

                THREE.MathUtils.degToRad(
                    this.angle / 2
                )

            ) * beamLength;


        // ----------------------------------------
        // BEAM SKALIEREN
        // ----------------------------------------

        this.beam.scale.set(

            radius,
            beamLength,
            radius

        );


        // ----------------------------------------
        // BEAM POSITION
        // ----------------------------------------

        this.beam.position.set(

            0,
            0,
            beamLength / 2

        );


        // ----------------------------------------
        // LICHTZIEL
        // ----------------------------------------

        this.lightTarget.position.set(

            0,
            0,
            beamLength

        );
    }


    // ========================================================
    // AUSWAHL
    // ========================================================

    setSelected(
        selected
    ) {

        if (selected) {

            this.base.material.emissive =
                new THREE.Color(
                    0x222222
                );

        } else {

            this.base.material.emissive =
                new THREE.Color(
                    0x000000
                );
        }
    }


    // ========================================================
    // LÖSCHEN
    // ========================================================

    remove() {

        if (
            selectedFixture === this
        ) {

            transformControls.detach();

        }


        scene.remove(
            this.group
        );


        this.group.traverse(
            object => {

                if (object.geometry) {

                    object.geometry.dispose();

                }


                if (object.material) {

                    if (
                        Array.isArray(
                            object.material
                        )
                    ) {

                        object.material.forEach(
                            material => {

                                material.dispose();

                            }
                        );

                    } else {

                        object.material.dispose();

                    }
                }
            }
        );
    }
}


// ============================================================
// FIXTURE HINZUFÜGEN
// ============================================================

function addFixture(
    position = new THREE.Vector3()
) {

    beginUndoAction();

    fixtureCounter++;


    const fixture =
        new MovingHead(

            fixtureCounter,

            position

        );


    fixtures.push(
        fixture
    );


    selectFixture(
        fixture
    );


    updateFixtureList();
    markProjectChanged();
    endUndoAction();
}


// ============================================================
// SETTINGS KOPIEREN
// ============================================================

document.getElementById(
    "copySettings"
).addEventListener(

    "click",

    () => {

        if (!selectedFixture) {

            alert(
                "Please select a Moving Head first."
            );

            return;

        }


        copiedSettings = {

            pan:
                selectedFixture.pan,

            tilt:
                selectedFixture.tilt,

            color:
                selectedFixture.color,

            intensity:
                selectedFixture.intensity,

            angle:
                selectedFixture.angle

        };


        alert(
            "Settings copied."
        );

    }

);
// ============================================================
// SETTINGS EINFÜGEN
// ============================================================

document.getElementById(
    "pasteSettings"
).addEventListener(

    "click",

    () => {

        if (!selectedFixture) {

            alert(
                "Please select a Moving Head first."
            );

            return;

        }


        if (!copiedSettings) {

            alert(
                "No settings copied yet."
            );

            return;

        }


        saveUndoState();


        selectedFixture.pan =
            copiedSettings.pan;

        selectedFixture.tilt =
            copiedSettings.tilt;

        selectedFixture.color =
            copiedSettings.color;

        selectedFixture.intensity =
            copiedSettings.intensity;

        selectedFixture.angle =
            copiedSettings.angle;


        selectedFixture.update();

        updateControls();

        markProjectChanged();


        alert(
            "Settings pasted."
        );

    }

);

// ============================================================
// FIXTURE LÖSCHEN
// ============================================================

function deleteSelectedFixture() {

    beginUndoAction();

    if (!selectedFixture) {
        return;
    }


    selectedFixture.remove();


    fixtures =
        fixtures.filter(

            fixture =>
                fixture !== selectedFixture

        );


    selectedFixture =
        null;


    transformControls.detach();


    updateFixtureList();
    clearPositionInputs();
    markProjectChanged();
    endUndoAction();
}


// ============================================================
// FIXTURE AUSWÄHLEN
// ============================================================

function selectFixture(
    fixture
) {

    if (
        selectedFixture === fixture
    ) {

        return;
    }


    if (selectedFixture) {

        selectedFixture.setSelected(
            false
        );
    }


    selectedFixture =
        fixture;


    if (selectedFixture) {

        selectedFixture.setSelected(
            true
        );


        transformControls.attach(
            selectedFixture.group
        );

    } else {

        transformControls.detach();

    }


    updateFixtureList();

    updateControls();
}


// ============================================================
// AUSWAHL AUFHEBEN
// ============================================================

function deselectFixture() {

    if (!selectedFixture) {
        return;
    }


    selectedFixture.setSelected(
        false
    );


    selectedFixture =
        null;


    transformControls.detach();


    updateFixtureList();

    clearPositionInputs();
}


// ============================================================
// FIXTURE-LISTE
// ============================================================

function updateFixtureList() {

    const list =
        document.getElementById(
            "fixtureList"
        );


    list.innerHTML = "";


    fixtures.forEach(
        fixture => {

            const element =
                document.createElement(
                    "div"
                );


            element.className =
                "fixture";


            if (
                fixture ===
                selectedFixture
            ) {

                element.classList.add(
                    "selected"
                );
            }


            element.textContent =
                `Moving Head ${fixture.id}`;


            element.addEventListener(
                "click",
                () => {

                    selectFixture(
                        fixture
                    );

                }
            );


            list.appendChild(
                element
            );
        }
    );
}


// ============================================================
// POSITIONS-INPUTS LEEREN
// ============================================================

function clearPositionInputs() {

    if (xInput) {
        xInput.value = "";
    }

    if (yInput) {
        yInput.value = "";
    }

    if (zInput) {
        zInput.value = "";
    }
}


// ============================================================
// POSITION VON INPUTS AUF FIXTURE ÜBERTRAGEN
// ============================================================

function updateFixturePosition() {

    if (!selectedFixture) {
        return;
    }


    const x =
        parseFloat(
            xInput.value
        );

    const y =
        parseFloat(
            yInput.value
        );

    const z =
        parseFloat(
            zInput.value
        );


    if (!Number.isNaN(x)) {

        selectedFixture.group.position.x =
            x;

    }


    if (!Number.isNaN(y)) {

        selectedFixture.group.position.y =
            y;

    }


    if (!Number.isNaN(z)) {

        selectedFixture.group.position.z =
            z;

    }


    markProjectChanged();
}


// ============================================================
// UI AKTUALISIEREN
// ============================================================

function updateControls() {

    if (!selectedFixture) {

        clearPositionInputs();

        return;
    }


    const fixture =
        selectedFixture;


    // ----------------------------------------
    // POSITION
    // ----------------------------------------

    if (xInput) {

        xInput.value =
            fixture.group.position.x.toFixed(2);

    }


    if (yInput) {

        yInput.value =
            fixture.group.position.y.toFixed(2);

    }


    if (zInput) {

        zInput.value =
            fixture.group.position.z.toFixed(2);

    }


    // ----------------------------------------
    // PAN
    // ----------------------------------------

    document.getElementById(
        "pan"
    ).value =
        fixture.pan;


    document.getElementById(
        "panValue"
    ).textContent =
        `${fixture.pan}°`;


    // ----------------------------------------
    // TILT
    // ----------------------------------------

    document.getElementById(
        "tilt"
    ).value =
        fixture.tilt;


    document.getElementById(
        "tiltValue"
    ).textContent =
        `${fixture.tilt}°`;


    // ----------------------------------------
    // FARBE
    // ----------------------------------------

    document.getElementById(
        "color"
    ).value =
        fixture.color;


    // ----------------------------------------
    // INTENSITÄT
    // ----------------------------------------

    document.getElementById(
        "intensity"
    ).value =
        fixture.intensity;


    document.getElementById(
        "intensityValue"
    ).textContent =
        fixture.intensity;


    // ----------------------------------------
    // BEAM ANGLE
    // ----------------------------------------

    document.getElementById(
        "beamAngle"
    ).value =
        fixture.angle;


    document.getElementById(
        "angleValue"
    ).textContent =
        `${fixture.angle}°`;
}


// ============================================================
// X / Y / Z INPUTS
// ============================================================

if (xInput) {

    xInput.addEventListener(
        "input",
        updateFixturePosition
    );

}


if (yInput) {

    yInput.addEventListener(
        "input",
        updateFixturePosition
    );

}


if (zInput) {

    zInput.addEventListener(
        "input",
        updateFixturePosition
    );

}


// ============================================================
// PAN
// ============================================================

document.getElementById(
    "pan"
).addEventListener(

    "input",

    event => {

        if (!selectedFixture) {
            return;
        }

        if (
            !event.target.dataset.undoSaved
        ) {

            saveUndoState();

            event.target.dataset.undoSaved =
                "true";

        }


        selectedFixture.pan =
            parseFloat(
                event.target.value
            );


        selectedFixture.update();

        markProjectChanged();


        document.getElementById(
            "panValue"
        ).textContent =
            `${selectedFixture.pan}°`;
    }
);


// ============================================================
// TILT
// ============================================================

document.getElementById(
    "tilt"
).addEventListener(

    "input",

    event => {

        if (!selectedFixture) {
            return;
        }


        selectedFixture.tilt =
            parseFloat(
                event.target.value
            );


        selectedFixture.update();

        markProjectChanged();


        document.getElementById(
            "tiltValue"
        ).textContent =
            `${selectedFixture.tilt}°`;
    }
);


// ============================================================
// FARBE
// ============================================================

document.getElementById(
    "color"
).addEventListener(

    "input",

    event => {

        if (!selectedFixture) {
            return;
        }


        selectedFixture.color =
            event.target.value;


        selectedFixture.update();

        markProjectChanged();
    }
);


// ============================================================
// INTENSITÄT
// ============================================================

document.getElementById(
    "intensity"
).addEventListener(

    "input",

    event => {

        if (!selectedFixture) {
            return;
        }


        selectedFixture.intensity =
            parseFloat(
                event.target.value
            );


        selectedFixture.update();

        markProjectChanged();


        document.getElementById(
            "intensityValue"
        ).textContent =
            selectedFixture.intensity;
    }
);


// ============================================================
// BEAM ANGLE
// ============================================================

document.getElementById(
    "beamAngle"
).addEventListener(

    "input",

    event => {

        if (!selectedFixture) {
            return;
        }


        selectedFixture.angle =
            parseFloat(
                event.target.value
            );


        selectedFixture.update();

        markProjectChanged();


        document.getElementById(
            "angleValue"
        ).textContent =
            `${selectedFixture.angle}°`;
    }
);


// ============================================================
// GLOBAL BEAM LÄNGE
// ============================================================

document.getElementById(
    "globalBeamLength"
).addEventListener(

    "input",

    event => {

        globalBeamLength =
            parseFloat(
                event.target.value
            );


        markProjectChanged();


        document.getElementById(
            "globalBeamLengthValue"
        ).textContent =
            `${globalBeamLength} m`;


        fixtures.forEach(
            fixture => {

                fixture.update();

            }
        );
    }
);


// ============================================================
// GLOBAL BEAM SICHTBARKEIT
// ============================================================

document.getElementById(
    "globalBeamToggle"
).addEventListener(

    "click",

    () => {

        globalBeamsVisible =
            !globalBeamsVisible;


        markProjectChanged();


        document.getElementById(
            "globalBeamToggle"
        ).textContent =
            globalBeamsVisible
                ? "Beam ON"
                : "Beam OFF";


        fixtures.forEach(
            fixture => {

                fixture.update();

            }
        );
    }
);


// ============================================================
// UNIVERSUM GRÖSSE
// ============================================================

document.getElementById(
    "universeSize"
).addEventListener(

    "input",

    event => {

        const size =
            parseFloat(
                event.target.value
            );


        markProjectChanged();


        document.getElementById(
            "universeSizeValue"
        ).textContent =
            `${size} m`;


        updateUniverseSize(
            size
        );
    }
);


// ============================================================
// MOVING HEAD HINZUFÜGEN
// ============================================================

document.getElementById(
    "addFixture"
).addEventListener(

    "click",

    () => {

        const offset =
            fixtures.length * 1.5;


        addFixture(

            new THREE.Vector3(

                offset,
                0,
                0

            )

        );
    }
);


// ============================================================
// MOVING HEAD LÖSCHEN
// ============================================================

document.getElementById(
    "deleteFixture"
).addEventListener(

    "click",

    () => {

        deleteSelectedFixture();

    }
);


// ============================================================
// HINT BUTTONS
// ============================================================

document.getElementById(
    "hintTranslate"
).addEventListener(

    "click",

    event => {

        event.preventDefault();


        if (selectedFixture) {

            transformControls.setMode(
                "translate"
            );

        }

    }
);


document.getElementById(
    "hintDeselect"
).addEventListener(

    "click",

    event => {

        event.preventDefault();


        if (selectedFixture) {

            deselectFixture();

        }

    }
);


document.getElementById(
    "hintRotate"
).addEventListener(

    "click",

    event => {

        event.preventDefault();


        if (selectedFixture) {

            transformControls.setMode(
                "rotate"
            );

        }

    }
);


// ============================================================
// TRANSFORM MODUS
// ============================================================

window.addEventListener(

    "keydown",

    event => {

        // ----------------------------------------
        // CTRL + S
        // ----------------------------------------

        if (
            event.ctrlKey &&
            event.key.toLowerCase() === "s"
        ) {

            event.preventDefault();

            saveProject();

            return;

        }

        // ----------------------------------------
        // CTRL + Z = UNDO
        // ----------------------------------------

        if (
            event.ctrlKey &&
            event.key.toLowerCase() === "z"
        ) {

            event.preventDefault();

            undo();

            return;

        }

        // ----------------------------------------
        // R = ROTATION
        // ----------------------------------------

        if (
            event.key.toLowerCase() === "r"
        ) {

            if (selectedFixture) {

                transformControls.setMode(
                    "rotate"
                );

            }

        }


        // ----------------------------------------
        // G = POSITION
        // ----------------------------------------

        if (
            event.key.toLowerCase() === "g"
        ) {

            if (selectedFixture) {

                transformControls.setMode(
                    "translate"
                );

            }

        }


        // ----------------------------------------
        // S = DESELECT
        // ----------------------------------------

        if (
            event.key.toLowerCase() === "s"
        ) {

            if (selectedFixture) {

                deselectFixture();

            }

        }


        // ----------------------------------------
        // DELETE
        // ----------------------------------------

        /*if (
            event.key === "Delete"
        ) {

            deleteSelectedFixture();

        }*/

    }
);


// ============================================================
// TRANSFORM ÄNDERUNGEN
// ============================================================

transformControls.addEventListener(

    "change",

    () => {

        if (!selectedFixture) {
            return;
        }


        updateControls();

        markProjectChanged();

    }
);


// ============================================================
// 3D-MOUSE-PICKING
// ============================================================

const raycaster =
    new THREE.Raycaster();


const mouse =
    new THREE.Vector2();


// ============================================================
// POSITION AUF BODEN BESTIMMEN
// ============================================================

const groundPlane =
    new THREE.Plane(

        new THREE.Vector3(
            0,
            1,
            0
        ),

        0

    );


const intersectionPoint =
    new THREE.Vector3();


// ============================================================
// MOUSE CLICK
// ============================================================

renderer.domElement.addEventListener(

    "pointerdown",

    event => {

        if (
            event.button !== 0
        ) {

            return;

        }


        if (
            transformControls.dragging
        ) {

            return;

        }


        const rect =
            renderer.domElement
                .getBoundingClientRect();


        mouse.x =
            (

                (event.clientX - rect.left) /
                rect.width

            ) * 2 - 1;


        mouse.y =
            -(

                (event.clientY - rect.top) /
                rect.height

            ) * 2 + 1;


        raycaster.setFromCamera(
            mouse,
            camera
        );


        // ----------------------------------------
        // FIXTURE SUCHEN
        // ----------------------------------------

        const objects = [];


        fixtures.forEach(

            fixture => {

                fixture.group.traverse(

                    object => {

                        if (
                            object.isMesh
                        ) {

                            objects.push(
                                object
                            );

                        }

                    }

                );

            }

        );


        const intersections =
            raycaster.intersectObjects(

                objects,

                true

            );


        // ----------------------------------------
        // FIXTURE GETROFFEN
        // ----------------------------------------

        if (
            intersections.length > 0
        ) {

            const clickedObject =
                intersections[0].object;


            let parent =
                clickedObject;


            while (

                parent &&

                !fixtures.some(

                    fixture =>
                        fixture.group === parent

                )

            ) {

                parent =
                    parent.parent;

            }


            if (parent) {

                const fixture =
                    fixtures.find(

                        fixture =>
                            fixture.group === parent

                    );


                if (fixture) {

                    selectFixture(
                        fixture
                    );


                    return;

                }
            }
        }


        // ----------------------------------------
        // SHIFT + CLICK
        // ----------------------------------------

        if (
            event.shiftKey &&
            selectedFixture
        ) {

            if (
                raycaster.ray.intersectPlane(

                    groundPlane,

                    intersectionPoint

                )
            ) {

                selectedFixture.group.position.x =
                    intersectionPoint.x;


                selectedFixture.group.position.z =
                    intersectionPoint.z;


                updateControls();

                markProjectChanged();

            }


            return;
        }


        // ----------------------------------------
        // KLICK DANEBEN
        // ----------------------------------------

        // deselectFixture();

    }
);


// ============================================================
// PROJEKT SPEICHERN / LADEN
// ============================================================

// ============================================================
// PROJEKT ALS JSON ERSTELLEN
// ============================================================

function getProjectData() {

    return {

        universeSize:
            universeSize,

        globalBeamLength:
            globalBeamLength,

        globalBeamsVisible:
            globalBeamsVisible,

        fixtures:
            fixtures.map(fixture => ({

                id:
                    fixture.id,

                position: {

                    x:
                        fixture.group.position.x,

                    y:
                        fixture.group.position.y,

                    z:
                        fixture.group.position.z

                },

                rotation: {

                    x:
                        fixture.group.rotation.x,

                    y:
                        fixture.group.rotation.y,

                    z:
                        fixture.group.rotation.z

                },

                pan:
                    fixture.pan,

                tilt:
                    fixture.tilt,

                color:
                    fixture.color,

                intensity:
                    fixture.intensity,

                angle:
                    fixture.angle

            }))

    };
}


// ============================================================
// PROJEKT SPEICHERN
// ============================================================

document.getElementById(
    "saveProject"
).addEventListener(

    "click",

    () => {

        saveProject();

    }

);


// ============================================================
// PROJEKT SPEICHERN
// ============================================================

async function saveProject() {

    const project =
        getProjectData();


    const saveButton =
        document.getElementById(
            "saveProject"
        );


    try {

        const response =
            await fetch(

                "/api/project/save",

                {

                    method: "POST",

                    headers: {

                        "Content-Type":
                            "application/json"

                    },

                    body:
                        JSON.stringify(
                            project
                        )

                }

            );


        const result =
            await response.json();


        if (!result.success) {

            throw new Error(

                result.error ||
                "Unbekannter Fehler"

            );

        }


        console.log(
            "Projekt gespeichert."
        );


        projectChanged =
            false;


        // ----------------------------------------------------
        // SAVE-BUTTON KURZ ZU HÄKCHEN ÄNDERN
        // ----------------------------------------------------

        saveButton.textContent =
            "✓";


        setTimeout(

            () => {

                saveButton.textContent =
                    "Save";

            },

            1500

        );


    } catch (error) {

        console.error(

            "Speichern fehlgeschlagen:",
            error

        );


        alert(
            "Projekt konnte nicht gespeichert werden."
        );

    }

}


// ============================================================
// PROJEKT BEIM START LADEN
// ============================================================

function loadInitialProject() {

    if (
        !initialProject ||
        !Array.isArray(initialProject.fixtures)
    ) {

        return;

    }


    // ----------------------------------------
    // UNIVERSUM
    // ----------------------------------------

    if (
        initialProject.universeSize !== undefined
    ) {

        universeSize =
            initialProject.universeSize;


        updateUniverseSize(
            universeSize
        );


        document.getElementById(
            "universeSize"
        ).value =
            universeSize;


        document.getElementById(
            "universeSizeValue"
        ).textContent =
            `${universeSize} m`;

    }


    // ----------------------------------------
    // GLOBALER BEAM
    // ----------------------------------------

    if (
        initialProject.globalBeamLength !== undefined
    ) {

        globalBeamLength =
            initialProject.globalBeamLength;


        document.getElementById(
            "globalBeamLength"
        ).value =
            globalBeamLength;


        document.getElementById(
            "globalBeamLengthValue"
        ).textContent =
            `${globalBeamLength} m`;

    }


    // ----------------------------------------
    // GLOBALER BEAM SICHTBARKEIT
    // ----------------------------------------

    if (
        initialProject.globalBeamsVisible !== undefined
    ) {

        globalBeamsVisible =
            initialProject.globalBeamsVisible;


        document.getElementById(
            "globalBeamToggle"
        ).textContent =
            globalBeamsVisible
                ? "Beam ON"
                : "Beam OFF";

    }


    // ----------------------------------------
    // FIXTURES
    // ----------------------------------------

    initialProject.fixtures.forEach(

        data => {

            const fixture =
                new MovingHead(

                    data.id,

                    new THREE.Vector3(

                        data.position?.x ?? 0,

                        data.position?.y ?? 0,

                        data.position?.z ?? 0

                    )

                );


            fixture.id =
                data.id;


            fixtureCounter =
                Math.max(

                    fixtureCounter,

                    fixture.id

                );


            // ----------------------------------------
            // ROTATION
            // ----------------------------------------

            fixture.group.rotation.set(

                data.rotation?.x ?? 0,

                data.rotation?.y ?? 0,

                data.rotation?.z ?? 0

            );


            // ----------------------------------------
            // PAN / TILT
            // ----------------------------------------

            fixture.pan =
                data.pan ?? 0;


            fixture.tilt =
                data.tilt ?? 0;


            // ----------------------------------------
            // LICHT
            // ----------------------------------------

            fixture.color =
                data.color ?? "#ffffff";


            fixture.intensity =
                data.intensity ?? 5;


            fixture.angle =
                data.angle ?? 20;


            fixture.update();


            fixtures.push(
                fixture
            );

        }

    );


    updateFixtureList();


    if (fixtures.length > 0) {

        selectFixture(
            fixtures[0]
        );

    }


    projectChanged =
        false;
}


// ============================================================
// RESIZE
// ============================================================

window.addEventListener(

    "resize",

    () => {

        const width =
            sceneContainer.clientWidth;


        const height =
            sceneContainer.clientHeight;


        camera.aspect =
            width / height;


        camera.updateProjectionMatrix();


        renderer.setSize(

            width,

            height

        );

    }

);

// ============================================================
// HISTORY SNAPSHOT ERSTELLEN
// ============================================================

function createHistorySnapshot() {

    return {
        project: JSON.parse(
            JSON.stringify(
                getProjectData()
            )
        ),

        selectedId:
            selectedFixture
                ? selectedFixture.id
                : null
    };
}


// ============================================================
// NEUE UNDO-AKTION BEGINNEN
// ============================================================

function beginUndoAction() {

    // Mehrfaches Aufrufen innerhalb
    // derselben Aktion verhindern

    if (historyActionOpen) {
        return;
    }

    undoStack.push(
        createHistorySnapshot()
    );

    // maximal 50 Schritte behalten

    if (
        undoStack.length >
        MAX_UNDO_STEPS
    ) {

        undoStack.shift();

    }

    // Neue Änderung löscht Redo-Historie

    redoStack = [];

    historyActionOpen = true;
}


// ============================================================
// AKTION BEENDEN
// ============================================================

function endUndoAction() {

    historyActionOpen = false;
}


// ============================================================
// PROJEKT-ZUSTAND WIEDERHERSTELLEN
// ============================================================

function restoreHistorySnapshot(
    snapshot
) {

    const state =
        snapshot.project;


    // ----------------------------------------
    // ALLE AKTUELLEN FIXTURES ENTFERNEN
    // ----------------------------------------

    transformControls.detach();

    selectedFixture = null;


    fixtures.forEach(
        fixture => {

            fixture.remove();

        }
    );


    fixtures = [];

    fixtureCounter = 0;


    // ----------------------------------------
    // UNIVERSUM
    // ----------------------------------------

    universeSize =
        state.universeSize;


    updateUniverseSize(
        universeSize
    );


    document.getElementById(
        "universeSize"
    ).value =
        universeSize;


    document.getElementById(
        "universeSizeValue"
    ).textContent =
        `${universeSize} m`;


    // ----------------------------------------
    // GLOBALER BEAM
    // ----------------------------------------

    globalBeamLength =
        state.globalBeamLength;


    document.getElementById(
        "globalBeamLength"
    ).value =
        globalBeamLength;


    document.getElementById(
        "globalBeamLengthValue"
    ).textContent =
        `${globalBeamLength} m`;


    // ----------------------------------------
    // BEAM SICHTBARKEIT
    // ----------------------------------------

    globalBeamsVisible =
        state.globalBeamsVisible;


    document.getElementById(
        "globalBeamToggle"
    ).textContent =
        globalBeamsVisible
            ? "Beam ON"
            : "Beam OFF";


    // ----------------------------------------
    // FIXTURES
    // ----------------------------------------

    state.fixtures.forEach(
        data => {

            const fixture =
                new MovingHead(

                    data.id,

                    new THREE.Vector3(

                        data.position?.x ?? 0,

                        data.position?.y ?? 0,

                        data.position?.z ?? 0

                    )

                );


            fixture.id =
                data.id;


            fixtureCounter =
                Math.max(
                    fixtureCounter,
                    fixture.id
                );


            // Rotation

            fixture.group.rotation.set(

                data.rotation?.x ?? 0,

                data.rotation?.y ?? 0,

                data.rotation?.z ?? 0

            );


            // Pan / Tilt

            fixture.pan =
                data.pan ?? 0;

            fixture.tilt =
                data.tilt ?? 0;


            // Licht

            fixture.color =
                data.color ?? "#ffffff";

            fixture.intensity =
                data.intensity ?? 5;

            fixture.angle =
                data.angle ?? 20;


            fixture.update();


            fixtures.push(
                fixture
            );

        }
    );


    // ----------------------------------------
    // UI
    // ----------------------------------------

    updateFixtureList();


    // ----------------------------------------
    // ALTE AUSWAHL WIEDERHERSTELLEN
    // ----------------------------------------

    if (
        snapshot.selectedId !== null
    ) {

        const fixture =
            fixtures.find(
                item =>
                    item.id ===
                    snapshot.selectedId
            );

        if (fixture) {

            selectFixture(
                fixture
            );

        } else {

            clearPositionInputs();

        }

    } else {

        clearPositionInputs();

    }


    updateControls();


    projectChanged = true;

    endUndoAction();
}


// ============================================================
// UNDO
// ============================================================

function undo() {

    if (
        undoStack.length === 0
    ) {

        console.log(
            "Keine Undo-Schritte vorhanden."
        );

        return;
    }


    // aktuellen Zustand für REDO speichern

    redoStack.push(
        createHistorySnapshot()
    );


    if (
        redoStack.length >
        MAX_UNDO_STEPS
    ) {

        redoStack.shift();

    }


    // letzten Zustand holen

    const snapshot =
        undoStack.pop();


    historyActionOpen = true;


    restoreHistorySnapshot(
        snapshot
    );


    console.log(
        `Undo: noch ${undoStack.length} Schritte`
    );
}


// ============================================================
// REDO
// ============================================================

function redo() {

    if (
        redoStack.length === 0
    ) {

        console.log(
            "Keine Redo-Schritte vorhanden."
        );

        return;
    }


    undoStack.push(
        createHistorySnapshot()
    );


    if (
        undoStack.length >
        MAX_UNDO_STEPS
    ) {

        undoStack.shift();

    }


    const snapshot =
        redoStack.pop();


    historyActionOpen = true;


    restoreHistorySnapshot(
        snapshot
    );


    console.log(
        `Redo: noch ${redoStack.length} Schritte`
    );
}


// ============================================================
// PROJEKT GEÄNDERT
// ============================================================

function markProjectChanged() {

    projectChanged =
        true;


    const saveButton =
        document.getElementById(
            "saveProject"
        );


    if (saveButton) {

        saveButton.textContent =
            "*Save";

    }

}


// ============================================================
// RENDER LOOP
// ============================================================

function animate() {

    requestAnimationFrame(
        animate
    );


    controls.update();


    renderer.render(

        scene,

        camera

    );

}


animate();


// ============================================================
// START
// ============================================================

if (
    initialProject &&
    Array.isArray(initialProject.fixtures) &&
    initialProject.fixtures.length > 0
) {

    loadInitialProject();

} else {

    addFixture(

        new THREE.Vector3(

            0,
            0,
            0

        )

    );

}